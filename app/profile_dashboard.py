"""The Profile page for a returning user: a fit-to-goal bar, three stats, the courses you are studying (with a progress ring each)
and a petal chart of how much of the role's skill list you cover.

Pure builders and logic live here (tested in tests/test_profile_dashboard.py); `render()` is the Streamlit part. Progress is set by
the user (0/25/50/75/100) and kept in st.session_state["study_progress"]. Only a finished course (100) changes your skill levels, so
the fit number moves when you finish one, never for a half-done course. Nothing here is invented: a course you have not touched is 0%."""

import copy

from app.ui import esc, icon

PROGRESS_STEPS = (0, 25, 50, 75, 100)
LEVEL_WORDS = {1: "Beginner", 2: "Intermediate", 3: "Expert"}
PETALS = 6
RING_R = 16


# --- logic ---------------------------------------------------------------------------------------------

def study_rows(steps: list[dict], courses: dict, progress: dict) -> list[dict]:
    """One dict per planned course, in plan order: title, provider, skill, level word, hours, percent done (0 if unset or not a step)."""
    out = []
    for s in steps:
        c = courses.get(s["course_id"], {})
        pct = progress.get(s["course_id"], 0)
        out.append({
            "course_id": s["course_id"], "title": c.get("title", s["course_id"]), "provider": c.get("provider"),
            "skill_id": s["skill_id"], "level_word": LEVEL_WORDS.get(c.get("level_out"), "Course"), "level_out": c.get("level_out"),
            "hours": s["hours"], "pct": pct if pct in PROGRESS_STEPS else 0, "url": s.get("url"),
        })
    return out


def hours_left(rows: list[dict]) -> float:
    return sum(r["hours"] * (100 - r["pct"]) / 100 for r in rows)


def plan_done_pct(rows: list[dict]) -> int:
    total = sum(r["hours"] for r in rows)
    return round(sum(r["hours"] * r["pct"] for r in rows) / total) if total else 0


def profile_with_completed(profile: dict, rows: list[dict], courses: dict) -> dict:
    """A copy of the profile where every course at 100% has raised its skill to the course's level (never lowered, added if new)."""
    out = copy.deepcopy(profile)
    levels = {s["skill_id"]: s for s in out["skills"]}
    for r in rows:
        level = courses.get(r["course_id"], {}).get("level_out")
        if r["pct"] != 100 or not level:
            continue
        if r["skill_id"] in levels:
            levels[r["skill_id"]]["level"] = max(levels[r["skill_id"]]["level"], level)
        else:
            entry = {"skill_id": r["skill_id"], "level": level}
            out["skills"].append(entry)
            levels[r["skill_id"]] = entry
    return out


def coverage(match: dict, name_of) -> list[tuple[str, int]]:
    """(skill name, percent of the required level you hold), heaviest skill first, for one ranked role."""
    items = [(c["weight"], c["skill_id"], c["user_level"], c["required_level"]) for c in match.get("contributions", [])]
    items += [(g["weight"], g["skill_id"], g["user_level"], g["required_level"]) for g in match.get("gaps", [])]
    items.sort(key=lambda t: -t[0])
    return [(name_of(sid), round(min(have / need, 1) * 100) if need else 100) for _w, sid, have, need in items]


# --- builders (one line of HTML, all data text escaped) ----------------------------------------------------------------

def goal_block(fit: int, fit_after: int, role_title: str) -> str:
    """The big fit number and a wide bar: solid up to your fit today, hatched up to the fit the finished plan could reach. The bar is fit,
    not course progress (that is the 'Plan done' stat)."""
    fit, fit_after = max(0, min(100, round(fit))), max(0, min(100, round(fit_after)))
    gain = ""
    if fit_after > fit:
        gain = f'<div class="sf-goal-gain sf-hatch" style="left:{fit}%;width:{fit_after - fit}%"></div>'
    return (
        f'<div class="sf-goal"><div class="sf-goal-num"><div class="sf-goal-big">{fit}</div>'
        f'<div class="sf-goal-cap">fit with {esc(role_title)}</div></div>'
        f'<div class="sf-goal-main"><div class="sf-goal-line"><b>{fit}% is your fit today</b>'
        f'<span> · finishing your plan could reach {fit_after}%, an estimate</span></div>'
        f'<div class="sf-goal-bar" role="img" aria-label="Fit {fit} percent; the plan reaches {fit_after} percent">'
        f'<div class="sf-goal-fill" style="width:{fit}%"></div>{gain}<div class="sf-goal-mark" style="left:{fit_after}%"></div></div></div></div>'
    )


def stat_columns(items: list[tuple]) -> str:
    """items = [(label, value, small line), ...]: three columns separated by hairlines."""
    cells = [f'<div class="sf-pstat"><div class="sf-pstat-label">{esc(label)}</div><div class="sf-pstat-value">{esc(value)}</div>'
             f'</div>' for label, value, *_ in items]
    return f'<div class="sf-pstats">{"".join(cells)}</div>'


def ring(pct: int) -> str:
    pct = max(0, min(100, int(pct)))
    return (f'<svg class="sf-ring" viewBox="0 0 40 40" role="img" aria-label="{pct} percent done"><circle class="sf-ring-bg" cx="20" cy="20" r="{RING_R}" pathLength="100"/>'
            f'<circle class="sf-ring-fg" cx="20" cy="20" r="{RING_R}" pathLength="100" stroke-dasharray="{pct} 100" transform="rotate(-90 20 20)"/></svg>')


def study_main(row: dict, skill_label_text: str) -> str:
    """The title and the skill (and provider) of one course you are studying."""
    return f'<div class="sf-study-main"><div class="sf-study-title">{esc(row["title"])}</div></div>'


def study_meta(row: dict) -> str:
    """The level chip, hours left (or Done) and the progress ring with its percent."""
    pct = row["pct"]
    left = "Done" if pct == 100 else f'{row["hours"] * (100 - pct) / 100:g} h left'
    return (f'<div class="sf-study-meta"><span class="sf-study-level">{icon("trending-up", 14)}<span>{esc(row["level_word"])}</span></span>'
            f'<span class="sf-study-left">{esc(left)}</span><span class="sf-study-pct">{ring(pct)}<span>{pct}%</span></span></div>')


def petal_chart(items: list[tuple[str, int]], fit: int) -> str:
    """Six hexagon petals around a centre disc. Each petal: a skill and the percent of the required level you hold; shaded by strength."""
    petals = []
    for i, (label, pct) in enumerate(items[:PETALS]):
        pct = max(0, min(100, int(pct)))
        tone = "hi" if pct >= 67 else "mid" if pct >= 34 else "lo"
        petals.append(f'<div class="sf-petal sf-petal-{i} sf-petal-{tone}"><b>{pct}%</b><span>{esc(label)}</span></div>')
    return (f'<div class="sf-petals" role="group" aria-label="How much of each skill this role needs you already hold">{"".join(petals)}'
            f'<div class="sf-petal-core"><b>{max(0, min(100, round(fit)))}%</b><span>fit</span></div></div>')


# --- the page ----------------------------------------------------------------------------------------------

def _set_progress(course_id: str) -> None:
    import streamlit as st

    st.session_state.setdefault("study_progress", {})[course_id] = st.session_state[f"study_pick_{course_id}"]


def render(profile: dict, snapshot: dict) -> bool:
    """Draw the dashboard. Returns False (draws nothing) when the plan or the engine can't give numbers, so the caller can show the
    plain summary instead."""
    import inspect

    import streamlit as st

    from app.ui import (
        card_container, course_catalog, role_catalog, role_skill_rows, run_engine, scenario, show, skill_label, skill_name,
        user_levels,
    )
    from engine import api
    from engine.pathway import plan

    result = run_engine(profile, snapshot)
    if not result or not result["matches"]:
        return False
    roles = role_catalog()
    ranked = [m["role_id"] for m in result["matches"]]
    preferred = st.session_state.get("plan_target")
    target_id = preferred if preferred in ranked else ranked[0]
    kwargs = {"budget_rm": profile.get("budget_rm")} if "budget_rm" in inspect.signature(plan).parameters else {}
    try:
        planned = plan(user_levels(profile["skills"]), roles[target_id], role_skill_rows(), list(course_catalog().values()),
                       result["forecasts"], snapshot, profile["risk_tolerance"], profile["hours_budget"], **kwargs)
    except ValueError:
        return False
    if not planned["steps"]:
        return False

    courses = course_catalog()
    progress = st.session_state.setdefault("study_progress", {})
    rows = study_rows(planned["steps"], courses, progress)
    fit_before = planned["before"]["match_pct"] * 100
    fit_after = planned["after"]["match_pct"] * 100
    fit_now = fit_before
    target_match = next(m for m in result["matches"] if m["role_id"] == target_id)
    if any(r["pct"] == 100 for r in rows):
        try:
            updated = api.analyse(profile_with_completed(profile, rows, courses), snapshot, scenario(), top_n=None)
            target_match = next(m for m in updated["matches"] if m["role_id"] == target_id)
            fit_now = target_match["match_pct"] * 100
        except (ValueError, StopIteration):
            pass
    finished = sum(r["pct"] == 100 for r in rows)
    initial = esc((profile.get("display_name") or "You")[:1].upper())

    show(f'<header class="sf-pagehead sf-profilehead"><h1 class="sf-title">Your profile</h1>'
         f'<div class="sf-whoami"><span class="sf-avatar" aria-hidden="true">{initial}</span>'
         f'<span>{esc(profile.get("display_name") or "You")}</span></div></header>')
    with card_container():
        show(goal_block(fit_now, fit_after, roles[target_id]["title"]))
        show(stat_columns([
            ("Skills you have", str(len(profile["skills"])), "in your profile"),
            ("Courses still to do", str(len(rows) - finished), f"{finished} done of {len(rows)}"),
            ("Hours left", f"{hours_left(rows):g} h", "an estimate, from your plan"),
            ("Plan done", f"{plan_done_pct(rows)}%", "of the planned hours"),
        ]))
    left, right = st.columns(2, gap="large")
    with left:
        with card_container():
            show('<div class="sf-ptitle"><b>Courses you are studying</b></div>')
            for i, row in enumerate(rows):
                with st.container(key=f"sf-study-{i}"):
                    body, control = st.columns([3, 2], gap="small", vertical_alignment="center")
                    body.markdown(study_main(row, skill_label(row["skill_id"])).replace("\n", " "), unsafe_allow_html=True)
                    with control.popover("Update", icon=":material/tune:", use_container_width=True):
                        st.radio(f"How far through {row['title']}?", PROGRESS_STEPS, index=PROGRESS_STEPS.index(row["pct"]),
                                 format_func=lambda p: f"{p}%", key=f"study_pick_{row['course_id']}", horizontal=True,
                                 on_change=_set_progress, args=(row["course_id"],))
                    show(study_meta(row))
    with right:
        with card_container():
            show('<div class="sf-ptitle"><b>Skills this role needs</b></div>')
            show(petal_chart(coverage(target_match, skill_name), round(fit_now)))
    return True
