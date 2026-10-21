"""Unit tests for the pure logic in app/onboarding.py (levels, resume intake, skill detection, building the profile)."""

import pytest

from app import onboarding as ob
from app.ui import SDG_NAMES
from engine import api
from engine.data import load_snapshot

RESUME = "Analyst. Built dashboards in Power BI and Excel, queried data with SQL, scripted reports in Python."


# --- levels --------------------------------------------------------------------------------------------

def test_level_mapping_round_trips():
    assert [ob.name_to_level(n) for n in ("basic", "working", "strong")] == [1, 2, 3]
    assert [ob.level_name(i) for i in (1, 2, 3)] == ["basic", "working", "strong"]
    assert ob.name_to_level(" Strong ") == 3


@pytest.mark.parametrize("bad", [0, 4, -1, None, True, "2"])
def test_level_name_rejects_bad_levels(bad):
    with pytest.raises(ValueError):
        ob.level_name(bad)


@pytest.mark.parametrize("bad", ["", "expert", None, "2"])
def test_name_to_level_rejects_bad_names(bad):
    with pytest.raises(ValueError):
        ob.name_to_level(bad)


# --- detection (the existing rule-based extractor, wired) ---------------------------------------------------

def test_detect_skills_finds_known_skills_in_catalog_order():
    ids, total = ob.detect_skills(RESUME)
    assert {"python", "sql", "excel", "powerbi"} <= set(ids)
    assert total == len(ids)
    catalog = ob.catalog_ids()
    assert ids == sorted(ids, key=catalog.index)


def test_detect_skills_empty_and_none_text():
    assert ob.detect_skills("") == ([], 0)
    assert ob.detect_skills(None) == ([], 0)


def test_go_in_a_sentence_is_not_the_go_language():
    ids, _ = ob.detect_skills("Go to our careers page and apply today. Go ahead and join us.")
    assert "golang" not in ids
    assert "golang" in ob.detect_skills("Services written in Go and Python.")[0]


def test_hostile_markup_is_just_text_to_the_matcher():
    ids, _ = ob.detect_skills("<script>alert(1)</script><img src=x onerror=alert(1)> Go to our careers page")
    assert ids == []


def test_detection_is_capped_with_the_true_total_reported():
    everything = " ".join(alias for row in ob._catalog_rows() for alias in row["aliases"] if not alias.startswith("cs:"))
    ids, total = ob.detect_skills(everything)
    assert len(ids) == ob.MAX_SKILLS
    assert total > ob.MAX_SKILLS


def test_text_beyond_the_cap_is_ignored():
    padded = "x " * (ob.MAX_TEXT_CHARS // 2 + 10) + " python"
    assert ob.detect_skills(padded)[0] == []


# --- intake ---------------------------------------------------------------------------------------------

def test_gather_text_combines_paste_and_txt_file():
    text = ob.gather_text("I know Python.", "cv.txt", b"and SQL")
    assert "Python" in text and "SQL" in text


def test_gather_text_needs_something():
    for args in ((None,), ("   ",), ("", None, None)):
        with pytest.raises(ob.ResumeError):
            ob.gather_text(*args)


def test_size_limit_is_enforced_on_uploads():
    ok = b"a" * ob.MAX_UPLOAD_BYTES
    assert ob.upload_text("cv.txt", ok)
    with pytest.raises(ob.ResumeError, match="larger than 2 MB"):
        ob.upload_text("cv.txt", ok + b"a")


@pytest.mark.parametrize("name,data", [("cv.docx", b"hello"), ("cv", b"hello"), ("cv.txt", b""), ("cv.txt", b"   \n"),
                                       ("cv.txt", b"abc\x00def")])
def test_bad_uploads_raise_resume_error(name, data):
    with pytest.raises(ob.ResumeError):
        ob.upload_text(name, data)


def test_txt_decoding_falls_back_for_non_utf8():
    assert "caf" in ob.upload_text("cv.txt", "café Python".encode("cp1252"))


def test_error_messages_never_echo_the_input():
    secret = b"%PDF-1.4 SECRET-RESUME-CONTENT not really a pdf"
    with pytest.raises(ob.ResumeError) as err:
        ob.pdf_text(secret)
    assert "SECRET" not in str(err.value)


needs_pypdf = pytest.mark.skipif(not ob.pdf_supported(), reason="pypdf not installed")


def _blank_pdf() -> bytes:
    import io

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@needs_pypdf
def test_scanned_or_blank_pdf_says_no_text_found():
    with pytest.raises(ob.ResumeError, match="No text found"):
        ob.upload_text("scan.pdf", _blank_pdf())


@needs_pypdf
def test_garbage_pdf_is_a_clear_error_not_a_traceback():
    with pytest.raises(ob.ResumeError, match="could not read"):
        ob.upload_text("cv.pdf", b"%PDF-1.4\nthis is not a real pdf at all")
    with pytest.raises(ob.ResumeError):
        ob.upload_text("cv.pdf", b"not a pdf")


@needs_pypdf
def test_pdf_with_text_is_read_in_memory():
    import io

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 150 Td (I use Python and SQL daily) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    buf = io.BytesIO()
    writer.write(buf)
    ids, _ = ob.detect_skills(ob.upload_text("cv.pdf", buf.getvalue()))
    assert {"python", "sql"} <= set(ids)


def test_missing_pypdf_gives_the_paste_only_message(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pypdf":
            raise ImportError("no pypdf")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ob.ResumeError, match="not available"):
        ob.pdf_text(b"%PDF-1.4 anything")


# --- building the profile ------------------------------------------------------------------------------------

def test_build_profile_has_exactly_the_contract_shape():
    profile = ob.build_profile([("python", 3), ("sql", 1)], hours=120, budget=0, risk="high", sdgs=[13, 4, 13])
    assert list(profile) == ["profile_id", "display_name", "synthetic", "headline", "hours_budget", "budget_rm",
                             "risk_tolerance", "sdg_interests", "skills"]
    assert profile["skills"] == [{"skill_id": "python", "level": 3}, {"skill_id": "sql", "level": 1}]
    assert profile["sdg_interests"] == [4, 13]
    assert (profile["hours_budget"], profile["budget_rm"], profile["risk_tolerance"]) == (120, 0, "high")
    assert profile["synthetic"] is False and profile["profile_id"] == "you"


def test_build_profile_drops_unknown_ids_and_duplicates():
    profile = ob.build_profile([("python", 2), ("not_a_skill", 3), ("python", 3), ["sql", 1]])
    assert profile["skills"] == [{"skill_id": "python", "level": 2}, {"skill_id": "sql", "level": 1}]


def test_build_profile_needs_a_known_skill():
    with pytest.raises(ValueError, match="at least one skill"):
        ob.build_profile([])
    with pytest.raises(ValueError, match="at least one skill"):
        ob.build_profile([("zzz", 1)])


@pytest.mark.parametrize("kwargs", [
    {"hours": 5}, {"hours": 2001}, {"hours": 10.5}, {"hours": True}, {"hours": float("nan")}, {"hours": None},
    {"budget": -1}, {"budget": 20001}, {"risk": "reckless"}, {"risk": None}, {"sdgs": [0]}, {"sdgs": [18]}, {"sdgs": ["8"]},
    {"sdgs": None},
])
def test_build_profile_validates_goals(kwargs):
    with pytest.raises(ValueError):
        ob.build_profile([("python", 1)], **kwargs)


@pytest.mark.parametrize("level", [0, 4, True, None, "2"])
def test_build_profile_validates_levels(level):
    with pytest.raises(ValueError, match="level"):
        ob.build_profile([("python", level)])


def test_built_profile_is_accepted_by_the_engine():
    ids, _ = ob.detect_skills(RESUME)
    profile = ob.build_profile([(sid, 2) for sid in ids], sdgs=[8])
    result = api.analyse(profile, load_snapshot("latest"), top_n=None)
    assert result["portfolio"]["readiness"] is not None


def test_goal_problems_lists_every_issue_in_plain_english():
    assert ob.goal_problems(200, 300, "medium", [1, 17]) == []
    problems = ob.goal_problems(1, -5, "x", [99])
    assert len(problems) == 4
    assert all(p.endswith(".") for p in problems)
    assert set(range(1, 18)) == set(SDG_NAMES)


# --- samples --------------------------------------------------------------------------------------------

def test_every_sample_profile_loads_and_builds_the_same_contract():
    ids = ob.sample_ids()
    assert len(ids) == 5
    for pid in ids:
        sample = ob.sample_profile(pid)
        assert sample["skills"] and not ob.goal_problems(sample["hours_budget"], sample["budget_rm"],
                                                          sample["risk_tolerance"], sample["sdg_interests"])
        api.analyse(sample, load_snapshot("latest"), top_n=None)
    assert ob.short_name({"display_name": "Aina (synthetic)"}) == "Aina"


# --- step indicator ------------------------------------------------------------------------------------------

def test_stepper_is_step_x_of_4_text_and_a_thin_bar_with_one_current_step():
    html = ob.stepper_html(3)                                   # wizard step 3 = step 2 of 4, Skills
    assert html.count('aria-current="step"') == 1 and "completed" in html and "not started" in html
    assert "Step 2 of 4: Skills" in html and 'role="progressbar"' in html and 'aria-valuenow="50"' in html
    for needle in ("Resume", "Skills", "Goals", "Your roles"):
        assert needle in html
    assert "[01]" not in html                                   # v4: plain text, no numbered mono steps
    assert html.count("<li ") == 4 and ob.STEPS == ("Resume", "Skills", "Goals", "Your roles")
    assert 'aria-current="step"' not in ob.stepper_html(1)      # the welcome comes before step 01
