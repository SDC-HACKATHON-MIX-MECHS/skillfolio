"""First-run onboarding wizard (resume first) for pages/1_Profile.py.

Two halves:
  * PURE LOGIC (no Streamlit calls): level mapping, resume text intake, skill detection, building the profile dict.
    Unit-tested in tests/test_onboarding.py.
  * WIZARD UI: `render()` draws the five steps (1 Welcome, 2 Resume, 3 Your skills, 4 Goals, 5 Done).

Privacy contract (the page tells the user this, so it must stay true):
  * Resume text is processed in memory only. It is never written to disk, never logged, and never kept in st.session_state
    after the "Find my skills" click: the callback reads it, keeps only the detected skill ids, then blanks the text box and
    discards the uploaded file.
  * Parsing is the repo's rule-based matcher (pipeline.extract_skills). When the RunPod endpoint is configured AND the user leaves
    "Also use our AI model" ticked, the text is also sent once to our own RunPod endpoint (app/runpod_client.py), which ranks
    skills from our catalogue only; our code does not store it. Unticked, or with no keys, the text goes nowhere else.

Session-state contract: the finished profile is stored in st.session_state["profile"] as
  {profile_id, display_name, synthetic, headline, hours_budget, budget_rm, risk_tolerance, sdg_interests, skills:[{skill_id, level}]}
which is exactly what pages 2-6 and engine.api.analyse read. Everything else the wizard keeps lives under "ob_*" keys.
"""

from __future__ import annotations

import copy
import functools
import importlib.util
import io
import logging
import re

from engine.data import list_profiles, load_profile, load_skills
from engine.guardrails import keep_known
from pipeline.extract_skills import compile_aliases, skills_in_text

# --- Limits and constants ---------------------------------------------------------------------------------
MAX_UPLOAD_BYTES = 2 * 1024 * 1024      # 2 MB per file
MAX_PASTE_CHARS = 20_000                # the text box refuses more than this
MAX_TEXT_CHARS = 100_000                # hard cap on text handed to the matcher (paste + file)
MAX_PDF_PAGES = 20
MAX_SKILLS = 30                         # more than this is cut off, with a warning
WARN_SKILLS = 20                        # a long list gets a gentle nudge
HOURS_MIN, HOURS_MAX, HOURS_STEP, HOURS_DEFAULT = 10, 2000, 10, 200
BUDGET_MIN, BUDGET_MAX, BUDGET_STEP, BUDGET_DEFAULT = 0, 20000, 50, 300
RISK_DEFAULT = "medium"

LEVEL_NAMES = ("basic", "working", "strong")          # shown to the user; stored as 1 / 2 / 3
LEVEL_HELP = "Basic: still learning it. Working: you use it at work. Strong: you could teach it."
STEPS = ("Resume", "Skills", "Goals", "Your roles")     # the numbered strip: [01] Resume [02] Skills [03] Goals [04] Your roles
STEP_INDEX = {2: 1, 3: 2, 4: 3, 5: 4}                  # wizard step (1 welcome .. 5 done) -> which numbered item is current
WELCOME_TITLE = "Your skills are a portfolio. AI is the market."
WELCOME_LEAD = ("See which of your skills employers want more or less, how much of that work AI already does, and what to learn next. "
                "It takes about two minutes. We never ask your age or gender.")

NOTICE = ("Please do not use a real resume or personal details in this competition demo: use a made-up or sample one. "
          "What you add is sent to this app's server, read in memory and discarded. We do not save it or pass it on.")
NOTICE_AI = ("Please do not use a real resume or personal details in this competition demo: use a made-up or sample one. "
             "What you add is read in memory on this app's server and discarded. If 'Also use our AI model' is ticked, the text is also "
             "sent once to our AI model on RunPod, which returns skill names; our code does not store it. We do not save it.")
AI_MODEL = "BAAI/bge-small-en-v1.5 on RunPod"
PDF_MISSING = "PDF upload is not available on this server, so paste the text or upload a .txt file instead."


class ResumeError(ValueError):
    """A problem with the resume input. The message is fixed text written for the user and never echoes resume content."""


# --- Pure logic: levels -----------------------------------------------------------------------------------

def level_name(level: int) -> str:
    """1 -> 'basic', 2 -> 'working', 3 -> 'strong'. Anything else raises ValueError."""
    if isinstance(level, bool) or level not in (1, 2, 3):
        raise ValueError(f"level must be 1, 2 or 3, got {level!r}")
    return LEVEL_NAMES[level - 1]


def name_to_level(name: str) -> int:
    """'basic' / 'Working' / 'STRONG' -> 1 / 2 / 3. Anything else raises ValueError."""
    key = str(name).strip().lower()
    if key not in LEVEL_NAMES:
        raise ValueError(f"level must be one of {LEVEL_NAMES}, got {name!r}")
    return LEVEL_NAMES.index(key) + 1


# --- Pure logic: skill catalog and detection --------------------------------------------------------------

@functools.cache
def _catalog_rows() -> tuple[dict, ...]:
    return tuple(load_skills())


@functools.cache
def _patterns() -> dict:
    return compile_aliases(list(_catalog_rows()))


def catalog_ids() -> list[str]:
    """Every skill id we track, in skills.csv order."""
    return [row["skill_id"] for row in _catalog_rows()]


def detect_skills(text: str) -> tuple[list[str], int]:
    """Skill ids the existing rule-based matcher finds in `text`, in catalog order, cut to MAX_SKILLS.
    Returns (ids, total_found) so the caller can warn when the list was cut. The text is not kept."""
    found = skills_in_text((text or "")[:MAX_TEXT_CHARS], _patterns())
    ordered = [sid for sid in catalog_ids() if sid in found]
    return ordered[:MAX_SKILLS], len(ordered)


# --- Pure logic: resume intake ----------------------------------------------------------------------------

def pdf_supported() -> bool:
    """True when pypdf can be imported (it is imported lazily, only when a PDF is actually read)."""
    return importlib.util.find_spec("pypdf") is not None


def pdf_text(data: bytes) -> str:
    """Text from a PDF held in memory. Raises ResumeError with a user-facing message; never touches disk."""
    if not data.startswith(b"%PDF"):
        raise ResumeError("This file does not look like a PDF. Paste the text instead.")
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ResumeError(PDF_MISSING) from None
    logging.getLogger("pypdf").setLevel(logging.CRITICAL)      # keep parser chatter (and anything it quotes) out of logs
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ResumeError("This PDF is password protected. Paste the text instead.")
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:MAX_PDF_PAGES])
    except ResumeError:
        raise
    except Exception:  # pypdf raises many types on damaged files; the message must not echo file content
        raise ResumeError("We could not read this PDF. Paste the text instead.") from None
    if not text.strip():
        raise ResumeError("No text found in this PDF (a scan is just a picture). Paste it instead.")
    return text


def upload_text(filename: str, data: bytes) -> str:
    """Text from an uploaded .txt or .pdf, entirely in memory. Raises ResumeError for size, type or unreadable files."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ResumeError(f"That file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. Paste the text instead.")
    if not data:
        raise ResumeError("That file is empty.")
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return pdf_text(data)
    if name.endswith(".txt"):
        if b"\x00" in data:
            raise ResumeError("That does not look like a plain text file. Paste the text instead.")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")
        if not text.strip():
            raise ResumeError("That file is empty.")
        return text
    raise ResumeError("Only .pdf and .txt files are supported.")


def gather_text(pasted: str | None, filename: str | None = None, data: bytes | None = None) -> str:
    """Pasted text plus any uploaded file's text, capped at MAX_TEXT_CHARS. Raises ResumeError if nothing usable."""
    parts: list[str] = []
    if pasted and pasted.strip():
        parts.append(pasted)
    if data is not None:
        parts.append(upload_text(filename or "", data))
    if not parts:
        raise ResumeError("Paste some text or attach a file first, or skip to pick skills yourself.")
    return "\n".join(parts)[:MAX_TEXT_CHARS]


# --- Pure logic: building the profile ---------------------------------------------------------------------

def _as_int(value, label: str) -> int:
    try:
        ok = not isinstance(value, bool) and isinstance(value, (int, float)) and int(value) == value
    except (ValueError, OverflowError):                   # nan, inf
        ok = False
    if not ok:
        raise ValueError(f"{label} must be a whole number")
    return int(value)


def goal_problems(hours, budget, risk, sdgs) -> list[str]:
    """Plain-English problems with the goals, empty when they are fine."""
    from app.ui import RISK_LABELS, SDG_NAMES

    problems = []
    try:
        if not HOURS_MIN <= _as_int(hours, "Hours") <= HOURS_MAX:
            problems.append(f"Learning hours must be between {HOURS_MIN} and {HOURS_MAX}.")
    except ValueError as exc:
        problems.append(str(exc) + ".")
    try:
        if not BUDGET_MIN <= _as_int(budget, "Budget") <= BUDGET_MAX:
            problems.append(f"Course budget must be between RM {BUDGET_MIN} and RM {BUDGET_MAX:,}.")
    except ValueError as exc:
        problems.append(str(exc) + ".")
    if risk not in RISK_LABELS:
        problems.append("Pick a risk tolerance: low, medium or high.")
    if not isinstance(sdgs, (list, tuple, set)) or any(isinstance(g, bool) or g not in SDG_NAMES for g in sdgs):
        problems.append("Sustainable Development Goals must be numbers 1 to 17.")
    return problems


def build_profile(skills, *, hours=HOURS_DEFAULT, budget=BUDGET_DEFAULT, risk=RISK_DEFAULT, sdgs=()) -> dict:
    """The profile dict every page reads. `skills` = [(skill_id, level 1-3), ...]. Unknown ids are dropped, duplicates
    keep the first level. Raises ValueError (message safe to show) when nothing valid is left or a goal is out of range."""
    problems = goal_problems(hours, budget, risk, sdgs)
    entries = []
    for pair in skills:
        sid, level = (pair["skill_id"], pair["level"]) if isinstance(pair, dict) else pair
        if isinstance(level, bool) or level not in (1, 2, 3):
            problems.append("Every skill needs a level: basic, working or strong.")
            break
        entries.append({"skill_id": sid, "level": int(level)})
    if problems:
        raise ValueError(" ".join(problems))
    unique, seen = [], set()
    for entry in keep_known(entries, "skill_id", set(catalog_ids())):
        if entry["skill_id"] not in seen:
            seen.add(entry["skill_id"])
            unique.append(entry)
    if not unique:
        raise ValueError("Add at least one skill to continue.")
    return {
        "profile_id": "you", "display_name": "You", "synthetic": False, "headline": "",
        "hours_budget": int(hours), "budget_rm": int(budget), "risk_tolerance": risk,
        "sdg_interests": sorted({int(g) for g in sdgs}),
        "skills": unique,
    }


def sample_profile(profile_id: str) -> dict:
    """One of the made-up sample profiles from data/profiles, with unknown skill ids dropped."""
    profile = copy.deepcopy(load_profile(profile_id))
    profile["skills"] = keep_known(profile["skills"], "skill_id", set(catalog_ids()))
    return profile


def sample_ids() -> list[str]:
    return list_profiles()


def short_name(profile: dict) -> str:
    """'Aina (synthetic)' -> 'Aina'."""
    return re.sub(r"\s*\(.*?\)\s*$", "", profile.get("display_name", "") or "").strip() or "Profile"


# =============================== Wizard UI =================================================================

def _ss():
    import streamlit as st

    return st.session_state


def _empty_goals() -> dict:
    return {"hours": HOURS_DEFAULT, "budget": BUDGET_DEFAULT, "risk": RISK_DEFAULT, "sdgs": []}


def _wipe_wizard_keys(keep: tuple[str, ...] = ()) -> None:
    ss = _ss()
    for key in [k for k in ss.keys() if isinstance(k, str) and k.startswith("ob_") and k not in keep]:
        del ss[key]


def _go(step: int) -> None:
    ss = _ss()
    ss["ob_error"] = None
    ss["ob_step"] = step


def _begin(step: int = 2) -> None:
    ss = _ss()
    ss["ob_skills"] = []
    ss["ob_goals"] = _empty_goals()
    ss["ob_note"] = None
    _go(step)


def _load_sample(profile_id: str) -> None:
    ss = _ss()
    _wipe_wizard_keys()
    ss["profile"] = sample_profile(profile_id)
    _go(5)


def _start_blank() -> None:
    """Blank path: no skills yet, so land on 'Your skills' to add some (a portfolio of nothing cannot be scored)."""
    ss = _ss()
    _wipe_wizard_keys()
    _begin(3)
    ss["ob_note"] = ("blank", 0, 0)


def _skip_resume() -> None:
    ss = _ss()
    ss["ob_error"] = None
    ss["ob_note"] = ("manual", 0, 0)
    _go(3)


def ai_extra(found: list[str], suggested: list[str] | None, limit: int = MAX_SKILLS) -> list[str] | None:
    """Catalogue skills the AI model suggested that keyword matching did not find, best first, within the skill limit.
    None stays None (the model was not reachable)."""
    if suggested is None:
        return None
    known, have = set(catalog_ids()), set(found)
    extra = [sid for sid in dict.fromkeys(suggested) if sid in known and sid not in have]
    return extra[:max(0, limit - len(found))]


def _ai_wanted() -> bool:
    from app import runpod_client
    return runpod_client.configured() and bool(_ss().get("ob_use_ai", True))


def _analyse_resume() -> None:
    """Callback for 'Find my skills'. The resume text lives only in local variables here: on success the text box is
    blanked and the upload widget is replaced, so nothing but the detected skill ids survives this function."""
    ss = _ss()
    n = ss.get("ob_upload_n", 0)
    upload = ss.get(f"ob_upload_{n}")
    ss["ob_error"] = None
    try:
        text = gather_text(
            ss.get("ob_resume_text"),
            getattr(upload, "name", None), upload.getvalue() if upload is not None else None,
        )
    except ResumeError as exc:
        ss["ob_error"] = str(exc)
        return
    found, total = detect_skills(text)
    ss["ob_ai"] = None
    if _ai_wanted():
        from app import runpod_client
        extra = ai_extra(found, runpod_client.suggest_skills(text, list(_catalog_rows())))
        ss["ob_ai"] = ("failed", []) if extra is None else ("ok", extra)
        found = found + (extra or [])
    del text
    old = dict(ss.get("ob_skills") or [])
    ss["ob_skills"] = [[sid, old.get(sid, 1)] for sid in found]
    ss["ob_note"] = ("resume", len(found), total)
    ss["ob_resume_text"] = ""
    ss["ob_upload_n"] = n + 1
    _go(3)


def _sync_levels() -> None:
    """Copy the level radios back into ob_skills (called after drawing and before any step change)."""
    ss = _ss()
    synced = []
    for sid, level in ss.get("ob_skills") or []:
        value = ss.get(f"ob_lvl_{sid}")
        synced.append([sid, name_to_level(value) if value in LEVEL_NAMES else level])
    ss["ob_skills"] = synced


def _leave_skills(step: int) -> None:
    _sync_levels()
    _go(step)


def _remove_skill(sid: str) -> None:
    ss = _ss()
    _sync_levels()
    ss["ob_skills"] = [e for e in ss["ob_skills"] if e[0] != sid]
    ss.pop(f"ob_lvl_{sid}", None)


def _add_skill() -> None:
    ss = _ss()
    sid = ss.get("ob_add_pick")
    ss["ob_add_pick"] = None
    _sync_levels()
    if sid and sid in set(catalog_ids()) and all(e[0] != sid for e in ss["ob_skills"]) and len(ss["ob_skills"]) < MAX_SKILLS:
        ss["ob_skills"].append([sid, 1])


def _read_goals() -> dict:
    ss = _ss()
    goals = dict(ss.get("ob_goals") or _empty_goals())
    for key, widget in (("hours", "ob_w_hours"), ("budget", "ob_w_budget"), ("risk", "ob_w_risk"), ("sdgs", "ob_w_sdgs")):
        if widget in ss:
            goals[key] = ss[widget]
    return goals


def _leave_goals(step: int) -> None:
    ss = _ss()
    ss["ob_goals"] = _read_goals()
    _go(step)


def _finish() -> None:
    ss = _ss()
    ss["ob_goals"] = goals = _read_goals()
    ss["ob_error"] = None
    try:
        ss["profile"] = build_profile(
            ss.get("ob_skills") or [], hours=goals["hours"], budget=goals["budget"], risk=goals["risk"], sdgs=goals["sdgs"],
        )
    except ValueError as exc:
        ss["ob_error"] = str(exc)
        return
    _go(5)


def _edit() -> None:
    ss = _ss()
    profile = ss["profile"]
    _wipe_wizard_keys()
    ss["ob_skills"] = [[e["skill_id"], e["level"]] for e in keep_known(profile["skills"], "skill_id", set(catalog_ids()))]
    ss["ob_goals"] = {
        "hours": profile["hours_budget"], "budget": profile["budget_rm"],
        "risk": profile["risk_tolerance"], "sdgs": list(profile["sdg_interests"]),
    }
    ss["ob_note"] = ("edit", len(ss["ob_skills"]), len(ss["ob_skills"]))
    _go(3)


def _ask_reset() -> None:
    _ss()["ob_confirm_reset"] = True


def _cancel_reset() -> None:
    _ss()["ob_confirm_reset"] = False


def _start_over() -> None:
    ss = _ss()
    _wipe_wizard_keys()
    ss.pop("profile", None)
    _go(1)


# --- Drawing ----------------------------------------------------------------------------------------------

def stepper_html(current: int) -> str:
    """The step indicator, the same numbered mono strip as Home's "how it works": [01] Resume [02] Skills [03] Goals
    [04] Your roles. `current` is the wizard step (1 welcome .. 5 done); the welcome has no active item. Earlier items get a
    tick, the current one is bold, underlined and has aria-current, so progress is never colour alone."""
    from app.ui import steps_html

    return steps_html(STEPS, STEP_INDEX.get(current), "Setup progress")


def _head(question: str, lead: str | None = None) -> None:
    """One question per step, in large type, with at most one plain sentence under it."""
    import streamlit as st

    st.header(question)
    if lead:
        st.markdown(lead)


def _step_welcome() -> None:
    import streamlit as st

    st.button("Start with my resume", type="primary", icon=":material/arrow_forward:", use_container_width=True,
              key="ob_start", on_click=_begin, args=(2,))
    with st.expander("Or try a demo profile"):
        st.caption("Made-up people. Loading one skips setup and opens their finished profile.")
        ids = sample_ids()
        for row in range(0, len(ids) + 1, 3):
            cols = st.columns(3)
            for col, pid in zip(cols, (ids + ["blank"])[row:row + 3]):
                if pid == "blank":
                    col.button("Blank profile", key="ob_demo_blank", use_container_width=True, on_click=_start_blank,
                               help="Start empty and add your own skills.")
                else:
                    sample = sample_profile(pid)
                    col.button(short_name(sample), key=f"ob_demo_{pid}", use_container_width=True, on_click=_load_sample,
                               args=(pid,), help=sample.get("headline") or None)


def _step_resume() -> None:
    import streamlit as st

    from app import runpod_client

    if runpod_client.configured():
        _head("Add your resume", "We look for skill names in it, and our AI model can suggest skills you describe without naming them. "
                                 "The text is cleared once we have your skills.")
    else:
        _head("Add your resume", "We look for skill names in it. No AI model reads it, and the text is cleared once we have your skills.")
    st.info(NOTICE_AI if runpod_client.configured() else NOTICE, icon=":material/shield:")
    error = _ss().get("ob_error")
    if error:
        st.error(error, icon=":material/error:")
    st.text_area(
        "Paste resume text", key="ob_resume_text", height=160, max_chars=MAX_PASTE_CHARS,
        placeholder="Paste a made-up or sample resume here",
    )
    pdf_ok = pdf_supported()
    with st.expander("Upload a file instead" if pdf_ok else "Upload a .txt file instead"):
        st.file_uploader(
            "A .pdf or .txt file, up to 2 MB" if pdf_ok else "A .txt file, up to 2 MB",
            type=["pdf", "txt"] if pdf_ok else ["txt"], key=f"ob_upload_{_ss().get('ob_upload_n', 0)}",
            help="The file is read in memory and discarded. Scanned PDFs have no text to read.",
        )
        if not pdf_ok:
            st.caption(PDF_MISSING)
    if runpod_client.configured():
        st.checkbox("Also use our AI model", value=True, key="ob_use_ai",
                    help=f"Sends the text once to our RunPod endpoint ({AI_MODEL}), which picks matching skills from our list only; our code does not store it.")
    st.button("Find my skills", type="primary", icon=":material/search:", use_container_width=True,
              key="ob_find", on_click=_analyse_resume)
    left, right = st.columns(2)
    left.button("Back", key="ob_back_1", type="tertiary", icon=":material/arrow_back:", on_click=_go, args=(1,))
    right.button("Skip, pick skills manually", key="ob_skip", type="tertiary", on_click=_skip_resume)


def _step_skills() -> None:
    import streamlit as st

    from app.ui import card_container, skill_label

    ss = _ss()
    note = ss.get("ob_note")
    skills = ss.get("ob_skills") or []
    _head("Do these look right?", "Set how well you know each skill. Remove any that are wrong, or add others.")
    if note and note[0] == "resume":
        _, kept, total = note
        if total == 0:
            st.info("We did not find any skills from our list in that text. Add yours below, or go back and try another resume.")
        else:
            st.success(f"We found {kept} skill{'s' if kept != 1 else ''}. Each starts at Basic, so set your real level.")
            if total > kept:
                st.warning(f"We found {total} skills and kept the first {MAX_SKILLS}. Remove any you do not use.")
        ai = ss.get("ob_ai")
        if ai and ai[0] == "ok" and ai[1]:
            st.info(f"Our AI model also suggested: {', '.join(skill_label(s) for s in ai[1])}. Remove any that are wrong.",
                    icon=":material/auto_awesome:")
        elif ai and ai[0] == "failed":
            st.caption("Our AI model did not answer in time, so we used keyword matching only.")
    elif note and note[0] in ("manual", "blank") and not skills:
        st.info("No skills yet. Search the list below to add the ones you have.")
    if len(skills) >= WARN_SKILLS:
        st.warning(f"That is {len(skills)} skills. A shorter list of what you really use gives a clearer picture.")
    st.caption(LEVEL_HELP)

    if skills:
        with card_container():
            for sid, level in skills:
                key = f"ob_lvl_{sid}"
                if key not in ss:
                    ss[key] = level_name(level)
                name_col, remove_col = st.columns([2, 1])
                name_col.radio(skill_label(sid), LEVEL_NAMES, key=key, horizontal=True, format_func=str.capitalize)
                remove_col.button("Remove", key=f"ob_rm_{sid}", type="tertiary", icon=":material/close:", use_container_width=True,
                                  on_click=_remove_skill, args=(sid,), help=f"Remove {skill_label(sid)} from your list.")
        _sync_levels()
        skills = ss["ob_skills"]
    chosen = {sid for sid, _ in skills}
    full = len(skills) >= MAX_SKILLS
    st.selectbox(
        "Add a skill (type to search)", options=[sid for sid in catalog_ids() if sid not in chosen], index=None,
        format_func=skill_label, key="ob_add_pick", on_change=_add_skill, disabled=full,
        placeholder="Search the skill list",
        help=f"You can add up to {MAX_SKILLS} skills." if full else None,
    )
    if full:
        st.caption(f"You have reached the limit of {MAX_SKILLS} skills.")
    st.button("Continue", type="primary", icon=":material/arrow_forward:", use_container_width=True,
              key="ob_to_goals", disabled=not skills, on_click=_leave_skills, args=(4,))
    if not skills:
        st.caption("Add at least one skill to continue.")
    st.button("Back", key="ob_back_2", type="tertiary", icon=":material/arrow_back:", on_click=_leave_skills, args=(2,))


def _step_goals() -> None:
    import streamlit as st

    from app.ui import RISK_LABELS, SDG_NAMES

    ss = _ss()
    goals = ss.get("ob_goals") or _empty_goals()
    _head("How much can you put into learning?", "This decides how many courses fit in your plan. You can change it later.")
    for key, widget in (("hours", "ob_w_hours"), ("budget", "ob_w_budget"), ("risk", "ob_w_risk"), ("sdgs", "ob_w_sdgs")):
        ss.setdefault(widget, goals[key])
    left, right = st.columns(2)
    left.number_input("Hours you can spend learning", min_value=HOURS_MIN, max_value=HOURS_MAX, step=HOURS_STEP, key="ob_w_hours",
                      help="Total hours you can spend learning in the next few months.")
    right.number_input("Course budget (RM)", min_value=BUDGET_MIN, max_value=BUDGET_MAX, step=BUDGET_STEP, key="ob_w_budget",
                       help="The most you would pay for courses. RM 0 means free courses only.")
    st.radio("How steady do you want your skills to be?", options=list(RISK_LABELS), format_func=RISK_LABELS.get, horizontal=True,
             key="ob_w_risk", help="Low favours skills whose hiring changes little from month to month. High accepts bigger swings for more growth.")
    with st.expander("Goals you care about (optional)"):
        st.multiselect(
            "UN Sustainable Development Goals", options=list(SDG_NAMES),
            format_func=lambda g: f"SDG {g} · {SDG_NAMES[g]}", key="ob_w_sdgs",
        )
    ss["ob_goals"] = g = _read_goals()
    problems = goal_problems(g["hours"], g["budget"], g["risk"], g["sdgs"])
    for problem in problems:
        st.error(problem, icon=":material/error:")
    if ss.get("ob_error") and not problems:
        st.error(ss["ob_error"], icon=":material/error:")
    st.button("See my profile", type="primary", icon=":material/arrow_forward:", use_container_width=True,
              key="ob_finish", disabled=bool(problems), on_click=_finish)
    st.button("Back", key="ob_back_3", type="tertiary", icon=":material/arrow_back:", on_click=_leave_goals, args=(3,))


def _summary(profile: dict, heading: str, lead: str) -> None:
    import streamlit as st

    from app.ui import RISK_LABELS, SDG_NAMES, esc, fmt_rm, show, skill_label, stat_row

    _head(heading, lead)
    who = esc(profile.get("display_name", "You")) + (f" · {esc(profile['headline'])}" if profile.get("headline") else "")
    st.markdown(f"**{who}**")
    show(stat_row([
        ("Skills", str(len(profile["skills"]))),
        ("Learning hours", f"{profile['hours_budget']} h"),
        ("Course budget", fmt_rm(profile["budget_rm"])),
    ]))
    with st.expander("Show my skills and goals"):
        goals = [SDG_NAMES[g] for g in profile["sdg_interests"] if g in SDG_NAMES]
        st.markdown("\n".join(f"- {esc(skill_label(e['skill_id']))}: {level_name(e['level']).capitalize()}" for e in profile["skills"]))
        st.caption(f"Steadiness: {RISK_LABELS.get(profile['risk_tolerance'], profile['risk_tolerance'])}"
                   + (" · Goals: " + ", ".join(goals) if goals else " · No goals picked"))


def _actions() -> None:
    import streamlit as st

    ss = _ss()
    if st.button("Open my portfolio", type="primary", icon=":material/arrow_forward:", use_container_width=True, key="ob_open"):
        st.switch_page("Home.py")
    left, right = st.columns(2)
    left.button("Edit", key="ob_edit", type="tertiary", icon=":material/edit:", on_click=_edit)
    right.button("Start over", key="ob_reset", type="tertiary", icon=":material/restart_alt:", on_click=_ask_reset)
    if ss.get("ob_confirm_reset"):
        st.warning("This clears your profile from this session. Start over?")
        yes, no = st.columns(2)
        yes.button("Yes, start over", key="ob_reset_yes", use_container_width=True, on_click=_start_over)
        no.button("Keep my profile", key="ob_reset_no", use_container_width=True, on_click=_cancel_reset)


def render() -> None:
    """Draw the right screen for the current state. Call once from pages/1_Profile.py after page_setup()."""
    from app.ui import page_head, show

    ss = _ss()
    profile = ss.get("profile")
    has_profile = bool(profile and profile.get("skills"))
    step = ss.get("ob_step")
    if step == 5 and not has_profile:
        step = ss["ob_step"] = 1
    if step is None:
        if has_profile:                                      # returning user: summary, not the wizard
            show(page_head("Your profile", narrow=True))
            _summary(profile, "Saved for this session", "Edit it, or open your portfolio.")
            _actions()
            return
        step = ss["ob_step"] = 1
    if step == 1:                                            # the welcome is the hero: serif word, one lead, one button
        show(page_head(WELCOME_TITLE, WELCOME_LEAD, narrow=True))
    else:
        show(page_head("Your profile", narrow=True))
    show(stepper_html(step))
    if step == 1:
        _step_welcome()
    elif step == 2:
        _step_resume()
    elif step == 3:
        _step_skills()
    elif step == 4:
        _step_goals()
    else:
        _summary(profile, "You are all set", "Open your portfolio to see how your skills line up with the job market.")
        _actions()
