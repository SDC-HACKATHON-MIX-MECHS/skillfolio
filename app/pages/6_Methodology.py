import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.page_components import concept_card, source_list
from app.ui import page_header, page_setup, section_header, show, source_note
from engine import config, forecast

snapshot = page_setup("Methodology")
page_header(
    "Methodology and sources",
    "Every number in SkillFolio comes from a public, dated source or from a setting listed on this page. "
    "Forecasts are estimates, not predictions. You make the decision.", narrow=True,
)

# --- Sources ----------------------------------------------------------------------------------------
USES = {
    "hn_whoishiring": "Job posts: how often each skill is mentioned, month by month.",
    "aei_job_exposure": "How much of each occupation's work AI already does (our AI impact number).",
    "onet_tech": "Which technologies each occupation uses. Links skills to occupations and to role skill lists.",
}
show(section_header("Where the data comes from", icon_name="file-text"))
# The Hacker News entry in the snapshot points at an API root that returns 404, so the page links the hiring account instead.
LINK_FIX = {"hn_whoishiring": "https://news.ycombinator.com/submitted?id=whoishiring"}
show(source_list([
    {"name": s["name"].replace(" — ", ": "), "use": USES.get(s["id"]), "licence": s["licence"], "retrieved": s["retrieved_at"][:10],
     "url": LINK_FIX.get(s["id"], s["url"])}
    for s in snapshot["sources"]
]))
st.caption(
    f"Snapshot {snapshot['snapshot_date']} covers {snapshot['months'][0]['month']} to {snapshot['months'][-1]['month']} "
    f"({len(snapshot['months'])} monthly Hacker News hiring threads)."
)

# --- How the numbers are made -----------------------------------------------------------------------
SCEN = config.SCENARIOS
# AI impact against hiring trend (before the AI scenario) across skills with enough data, from the snapshot loaded on this page.
_fc = forecast.forecast_all(snapshot)
_pairs = [(f["exposure"], f["momentum"]) for f in _fc.values() if f["exposure"] is not None and not f["thin_data"]]
try:
    _r = statistics.correlation(*zip(*_pairs)) if len(_pairs) >= 3 else None
except statistics.StatisticsError:
    _r = None
if _r is None:
    LINK_SENTENCE = "There were too few well-observed skills to compare AI impact with hiring growth."
else:
    _r = 0.0 if round(_r, 2) == 0 else _r
    LINK_SENTENCE = (
        f"On the {snapshot['snapshot_date']} snapshot, the link between AI impact and hiring growth was {_r:+.2f} "
        f"among {len(_pairs)} well-observed skills (0 means no link), "
        + ("so today's posts do not yet show AI-exposed skills falling. " if abs(_r) < 0.2
           else "so the posts do show some link, but it is weak evidence on its own. ")
        + "The scenario weights are assumptions."
    )
show(section_header("How the numbers are made", icon_name="line-chart"))
show(
    concept_card("Job-post demand (demand index)", [
        f"For each of the {len(snapshot['months'])} months in the snapshot we count the share of Hacker News hiring posts that mention a skill. "
        f"To smooth the noise, each month becomes the average of the last {config.SMOOTHING_MONTHS} months. Then we set the first month in which the skill is mentioned to 100.",
        "A post that mentions a skill five times counts once.",
    ]),
    concept_card("Hiring trend (momentum)", [
        f"We fit a straight line to the last {config.MOMENTUM_WINDOW_MONTHS} months of the smoothed share, on a log scale, and turn its slope into a yearly percent change. "
        f"The noisier a skill's trend, the more it is pulled toward the average of all skills. This needs at least {config.SHRINK_MIN_SKILLS} well-observed skills to work out that average. With fewer, nothing is pulled.",
        f"Then the AI scenario moves each skill by how far its AI impact is above or below the average. "
        f"{SCEN['moderate']['label']} uses a weight of {SCEN['moderate']['lambda']:g}; {SCEN['fast']['label']} uses {SCEN['fast']['lambda']:g}. "
        "These weights are our assumptions, not numbers measured from data.",
        f"A skill is labelled rising when its whole approximate range is above +{config.TREND_THRESHOLD:.0%} a year, declining when it is below −{config.TREND_THRESHOLD:.0%}, otherwise stable. "
        f"A skill with fewer than {config.THIN_DATA_MIN_MEAN_COUNT} posts a month on average, or fewer than {config.MIN_HISTORY_MONTHS} months of history, is shown as not enough data and labelled stable.",
    ], "yearly change = e^(damped yearly log slope − λ × (skill AI impact − average AI impact)) − 1"),
    concept_card("How reliable the ranges are (uncertainty band)", [
        f"Each trend comes with a range. It is designed as an 80% range, but it is approximate. The trend is fitted to a {config.SMOOTHING_MONTHS}-month average, so neighbouring points move together and the plain error bar is too narrow, by about {config.SE_INFLATION:g} times.",
        f"We widen it by {config.SE_INFLATION:g} (the standard-error inflation). In one simulation with a flat true trend (described in docs/SPEC.md), the widened range contained the truth about 76% of the time; without widening it did so only about 48% of the time. "
        "This is one constant fitted on one simulation, so treat every range as indicative.",
    ]),
    concept_card("Outlook score (readiness)", [
        "Your hiring trend, minus a penalty for how much hiring for your skills bounces around, scaled by the risk you said you accept. Higher is better. It is an estimate.",
        f"Your skills are weighted by level (1 basic, 2 working, 3 strong), so weight = your level divided by the sum of your levels. A skill with not enough data counts for at most ±{config.THIN_GROWTH_CAP:.0%} a year in your hiring trend. "
        f"The penalty weight is {config.RISK_AVERSION['low']:g} for low, {config.RISK_AVERSION['medium']:g} for medium and {config.RISK_AVERSION['high']:g} for high risk.",
    ], "outlook = hiring trend − (penalty weight ÷ 2) × (how much hiring bounces around)²"),
    concept_card("AI impact (AI exposure)", [
        "From the Anthropic Economic Index. Of the tasks language models could speed up in an occupation, it measures how many are actually done that way at work. Fully automated use counts in full, human-plus-AI use counts half, weighted by time spent on each task.",
        "It means the work is changing fastest, not that the job disappears. Anthropic's own research (5 March 2026) found no systematic rise in unemployment for highly exposed workers since late 2022.",
        "The skill-level number is ours: the average over the O*NET occupations that use the skill (or a stand-in occupation when none is listed).",
    ]),
    concept_card("Fit with a role (role match)", [
        "For each skill a role needs, you earn credit for your level against the level required, up to full credit, weighted by how important the skill is for that role (importance 1 to 3). Fit is the weighted total, as a percentage.",
        "The words on a role card are a display rule of ours, not an engine result: Strong fit is a fit of 70% or more, Good fit is 40 to 69%, Stretch is below 40%.",
        f"Roles are ranked by a rank score, not by fit alone. The score is your fit, multiplied by one plus the role's demand growth, multiplied by one plus {config.SDG_TILT_ALPHA:g} times the share of the SDGs you chose that the role covers. "
        f"Role growth is the importance-weighted average of the yearly change of its skills (a skill with not enough data counts for at most ±{config.THIN_GROWTH_CAP:.0%}). Only roles you could move into are ranked.",
    ], f"fit = sum of weight × min(your level ÷ required level, 1) ÷ sum of weight; rank = fit × (1 + role growth) × (1 + {config.SDG_TILT_ALPHA:g} × share of your chosen SDGs the role covers)"),
    concept_card("Where your skills point (SDG allocation)", [
        f"Every skill supports SDG {config.BASELINE_SKILL_SDG} (target 4.4, relevant skills for decent jobs). A skill also supports the SDGs of every role that rates it at least {config.ROLE_SDG_MIN_WEIGHT} in importance.",
        f"Each skill's weight is split equally across its goals. Because every skill carries SDG {config.BASELINE_SKILL_SDG}, it is never smaller than any other slice, so the story is in the other slices.",
    ]),
    concept_card("Your learning plan (planner)", [
        "The planner is greedy: it picks one course at a time and does not look ahead. Each round it gives every allowed course a gain per hour. "
        f"The gain is the rise in your outlook score plus the rise in your fit with the target role (fit counted as a number from 0 to 1, at weight {config.PATHWAY_MATCH_BETA:g}), divided by the course hours. "
        "Ties go to the cheaper course.",
        "A course is allowed if it comes from our course list, teaches a skill the target role needs at a level above yours, fits your remaining hours (and money, if you set a limit), and has its prerequisite met by your current levels. "
        "The best course is added, that skill moves up to the level the course teaches, and the round repeats. "
        "A step can lower your outlook score if the rise in fit outweighs the drop. The plan stops when no course has a gain above zero.",
        "Hours, costs and links come from courses.csv. Each course row records the date its link was last checked.",
    ]),
)

# --- Assumptions ------------------------------------------------------------------------------------
show(section_header("What we assume", icon_name="info"))
with st.expander("Show every setting"):
    rows = [{"Setting": f"{v['label']}: AI weight (λ)", "Value": v["lambda"]} for v in config.SCENARIOS.values()]
    st.dataframe(pd.DataFrame(rows + [
        {"Setting": "Months averaged to smooth noise", "Value": config.SMOOTHING_MONTHS},
        {"Setting": "Months used for the hiring trend (momentum)", "Value": config.MOMENTUM_WINDOW_MONTHS},
        {"Setting": "Months used for how much hiring bounces around (volatility)", "Value": config.VOLATILITY_WINDOW_MONTHS},
        {"Setting": "Rising / declining threshold (per year)", "Value": f"±{config.TREND_THRESHOLD:.0%}"},
        {"Setting": "Range around the trend (designed as)", "Value": "80%"},
        {"Setting": "Widening of the range (standard-error inflation)", "Value": config.SE_INFLATION},
        {"Setting": "Not enough data below (posts a month)", "Value": config.THIN_DATA_MIN_MEAN_COUNT},
        {"Setting": "Months of history needed for a trend", "Value": config.MIN_HISTORY_MONTHS},
        {"Setting": "Cap on a skill with not enough data (per year)", "Value": f"±{config.THIN_GROWTH_CAP:.0%}"},
        {"Setting": "Risk penalty weight (low / medium / high)", "Value": " / ".join(f"{v:g}" for v in config.RISK_AVERSION.values())},
        {"Setting": "How far the skill-to-skill swing table is pulled toward plain per-skill swings (covariance shrinkage)", "Value": f"{config.COVARIANCE_SHRINKAGE:.0%}"},
        {"Setting": "Lift for roles that share your SDGs (α)", "Value": config.SDG_TILT_ALPHA},
    ]).astype({"Value": str}), hide_index=True, use_container_width=True)
    source_note("the settings file engine/config.py")

# --- Limits -----------------------------------------------------------------------------------------
show(section_header("What this cannot tell you", icon_name="info"))
st.markdown(
    "- SkillFolio covers tech and data roles only. Hacker News hiring posts lean towards the United States and remote jobs, "
    "so they may not match hiring elsewhere. Malaysian occupation data is a later upgrade.\n"
    "- Your skill levels are self-reported. We do not test them, so your scores are only as good as what you enter.\n"
    "- Every forecast, range and score here is an estimate, not a prediction.\n"
    "- AI impact measures how much AI is already used on a job's tasks. It is **not** a forecast of job loss.\n"
    f"- The scenarios are a what-if, not a prediction. {LINK_SENTENCE}\n"
    "- Skills are found in posts with fixed text rules. Short names such as Go or R must match in capital letters, so some posts may be miscounted.\n"
    "- Skills with not enough data are greyed and capped in your hiring trend, but their ups and downs are not capped, so the outlook score leans cautious if you hold rare skills.\n"
    "- Trends are pulled toward the average of all skills, so a skill that is truly growing very fast shows somewhat closer to average.\n"
    "- We never ask your age or gender, and none are used in scoring."
)

# --- AI disclosure ----------------------------------------------------------------------------------
show(section_header("AI disclosure", icon_name="user"))
st.markdown(
    "- **In the product:** forecasts and plans use statistics, not AI models. To read a resume, the app also uses an open "
    "embedding model, BAAI/bge-small-en-v1.5 (MIT licence), running on a RunPod GPU (optional: used only when the endpoint keys are set, and the user can untick it). It can only suggest skills from our own "
    "list, you can remove any that are wrong, and without it the app matches your resume with fixed keyword rules. "
    "SkillFolio keeps no copy of your resume text. No generative language model is used.\n"
    "- **While building:** we used Claude Code (Anthropic) to help write code, tests, data files and documents, and "
    "Replit Agent to help build pages. The team reviews all logic, runs the tests before merging, and merges changes through pull requests."
)
