"""Checks every data file against contracts/README.md. Must always pass."""

import re

from engine import data

SOC_RE = re.compile(r"^\d{2}-\d{4}$")
FORBIDDEN_PROFILE_KEYS = {"age", "gender", "sex", "race", "ethnicity", "religion", "date_of_birth"}


def test_skills_unique_and_complete():
    skills = data.load_skills()
    ids = [s["skill_id"] for s in skills]
    tickers = [s["ticker"] for s in skills]
    assert len(ids) == len(set(ids)), "duplicate skill_id"
    assert len(tickers) == len(set(tickers)), "duplicate ticker"
    for s in skills:
        assert s["name"] and s["aliases"], f"{s['skill_id']} needs a name and aliases"
        for soc in s["proxy_soc_codes"]:
            assert SOC_RE.match(soc), f"{s['skill_id']}: bad proxy SOC {soc}"


def test_roles_have_exposure_and_sdgs():
    roles = data.load_roles()
    ids = [r["role_id"] for r in roles]
    assert len(ids) == len(set(ids)), "duplicate role_id"
    for r in roles:
        assert r["role_type"] in {"future", "origin"}
        assert SOC_RE.match(r["soc_code"]), f"{r['role_id']}: bad SOC {r['soc_code']}"
        assert 0 <= r["ai_exposure"] <= 1
        assert r["sdgs"] and all(1 <= g <= 17 for g in r["sdgs"]), f"{r['role_id']} needs SDGs 1-17"
        assert r["sdg_rationale"], f"{r['role_id']} needs an SDG reason"
        assert r["sdg_source_url"].startswith("https://"), f"{r['role_id']} needs an SDG source"


def test_profiles_reference_known_skills_and_stay_fair():
    skill_ids = {s["skill_id"] for s in data.load_skills()}
    for pid in data.list_profiles():
        p = data.load_profile(pid)
        assert p["synthetic"] is True, f"{pid} must be synthetic"
        assert not FORBIDDEN_PROFILE_KEYS & set(p), f"{pid} has a protected attribute"
        assert p["risk_tolerance"] in {"low", "medium", "high"}
        assert all(1 <= g <= 17 for g in p["sdg_interests"])
        for s in p["skills"]:
            assert s["skill_id"] in skill_ids, f"{pid}: unknown skill {s['skill_id']}"
            assert 1 <= s["level"] <= 3


def test_role_skills_reference_known_ids():
    skill_ids = {s["skill_id"] for s in data.load_skills()}
    role_ids = {r["role_id"] for r in data.load_roles()}
    for row in data.load_role_skills():
        assert row["role_id"] in role_ids, f"unknown role {row['role_id']}"
        assert row["skill_id"] in skill_ids, f"unknown skill {row['skill_id']}"
        assert 1 <= row["weight"] <= 3 and 1 <= row["required_level"] <= 3


def test_courses_are_sourced():
    skill_ids = {s["skill_id"] for s in data.load_skills()}
    ids = [c["course_id"] for c in data.load_courses()]
    assert len(ids) == len(set(ids)), "duplicate course_id"
    for c in data.load_courses():
        assert c["skill_id"] in skill_ids, f"{c['course_id']}: unknown skill"
        assert c["url"].startswith("https://"), f"{c['course_id']}: needs a working https URL"
        assert c["hrdc_claimable"] in {"yes", "no", "unknown"}
        assert c["verified_on"], f"{c['course_id']}: needs verified_on"
        assert 1 <= c["level_out"] <= 3 and c["hours"] > 0 and c["cost_rm"] >= 0
        if c["prereq_skill_id"]:
            assert c["prereq_skill_id"] in skill_ids
