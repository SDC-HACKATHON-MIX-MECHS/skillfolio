"""Smoke tests: every page runs without an exception, with no profile and with the sample profile 'aina' loaded.

The profile lives in st.session_state["profile"] (set by pages/1_Profile.py, read by app.ui.require_profile).
Also lints the page files for the two rules the redesign adds: no hex colours and no emoji outside app/ui.py.
"""

import json
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
PAGES = sorted((APP / "pages").glob("*.py"))
TIMEOUT = 60


def sample_profile(profile_id: str = "aina") -> dict:
    return json.loads((ROOT / "data" / "profiles" / f"{profile_id}.json").read_text(encoding="utf-8"))


def run(script: Path, profile: dict | None) -> AppTest:
    """Run Home.py as the entrypoint (page_link paths are relative to it); for a page, switch to it afterwards."""
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=TIMEOUT)
    if profile is not None:
        at.session_state["profile"] = profile
    at.run()
    if script.name != "Home.py":
        at.switch_page(f"pages/{script.name}").run()
    return at


def test_home_without_profile_shows_welcome_and_one_primary_button():
    # Home v2 (details in tests/test_home_v2.py): one primary button plus a small demo link
    at = run(APP / "Home.py", None)
    assert not at.exception
    assert [b.label for b in at.button] == ["Set up my portfolio", "Try this example"]
    assert at.button[0].proto.type == "primary"


@pytest.mark.parametrize("profile_id", ["aina", "priya"])
def test_home_with_sample_profile_renders_skills_section(profile_id):
    at = run(APP / "Home.py", sample_profile(profile_id))
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "How your skills are doing" in html
    assert "Set up my portfolio" not in [b.label for b in at.button]


@pytest.mark.parametrize("script", [APP / "Home.py", *PAGES], ids=lambda p: p.name)
def test_every_page_runs_with_the_sample_profile(script):
    assert not run(script, sample_profile()).exception


@pytest.mark.parametrize("script", PAGES, ids=lambda p: p.name)
def test_every_page_runs_without_a_profile(script):
    assert not run(script, None).exception


# --- Lint: no hex codes, no emoji in page files (tokens and icons live in app/ui.py) ----------------------

# Pages the other redesign agents are still converting; remove a name from this set when its page is done.
NOT_YET_CONVERTED: set[str] = set()
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")


@pytest.mark.parametrize("script", [APP / "Home.py", *PAGES], ids=lambda p: p.name)
def test_page_files_have_no_hex_codes_or_emoji(script):
    if script.name in NOT_YET_CONVERTED:
        pytest.skip("page not yet converted to the new design system")
    text = script.read_text(encoding="utf-8")
    assert not HEX.findall(text), "use tokens from app/ui.py, not hex codes"
    assert not EMOJI.findall(text), "use :material/...: icons or app.ui.icon(), not emoji"
