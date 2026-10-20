"""Tests for pipeline.load_exposure and pipeline.build_snapshot on small in-memory data (no downloads)."""

import csv
import io
import zipfile

from pipeline import build_snapshot, load_exposure

SKILLS = [
    {"skill_id": "python", "aliases": ["python"], "onet_examples": ["Python"], "proxy_soc_codes": []},
    {"skill_id": "customer_success", "aliases": ["customer success"], "onet_examples": [], "proxy_soc_codes": ["43-4051"]},
    {"skill_id": "nothing", "aliases": ["nothing"], "onet_examples": ["Not In ONET"], "proxy_soc_codes": []},
]
EXPOSURE = {"15-1252": 0.3, "15-2051": 0.5, "43-4051": 0.7}
ONET = [
    {"O*NET-SOC Code": "15-1252.00", "Example": "Python", "Hot Technology": "Y", "In Demand": "Y"},
    {"O*NET-SOC Code": "15-2051.00", "Example": "Python", "Hot Technology": "Y", "In Demand": "N"},
    {"O*NET-SOC Code": "15-2051.01", "Example": "Python", "Hot Technology": "N", "In Demand": "N"},
    {"O*NET-SOC Code": "99-9999.00", "Example": "Python", "Hot Technology": "N", "In Demand": "N"},  # no exposure
]


def test_skill_exposure_methods():
    out = load_exposure.skill_exposure(SKILLS, EXPOSURE, ONET)
    assert out["python"] == {"exposure": 0.4, "exposure_n_occupations": 2, "exposure_method": "onet_tech"}
    assert out["customer_success"] == {"exposure": 0.7, "exposure_n_occupations": 1, "exposure_method": "proxy"}
    assert out["nothing"] == {"exposure": None, "exposure_n_occupations": 0, "exposure_method": None}


def test_generate_role_skills_weights():
    roles = [{"role_id": "dev", "soc_code": "15-1252"}, {"role_id": "ds", "soc_code": "15-2051"}]
    rows = load_exposure.generate_role_skills(roles, SKILLS, ONET)
    assert rows == [
        {"role_id": "dev", "skill_id": "python", "weight": 3, "required_level": 2, "source": "onet_in_demand"},
        {"role_id": "ds", "skill_id": "python", "weight": 2, "required_level": 2, "source": "onet_hot"},
    ]


def test_read_onet_tech_handles_31_0_layout(tmp_path):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["O*NET-SOC Code", "Title", "Workplace Example", "Element ID", "Element Name", "Hot Technology", "In Demand"])
    w.writerow(["15-1252.00", "Software Developers", "Python", "2.E.x", "Object oriented", "Y", "Y"])
    path = tmp_path / "onet.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("db_31_0_csv/software_skills.csv", "﻿" + buf.getvalue())
    rows = load_exposure.read_onet_tech(path)
    assert rows[0]["Example"] == "Python" and rows[0]["O*NET-SOC Code"] == "15-1252.00"


def test_assemble_matches_contract():
    raw = [
        {"month": "2026-10", "story_id": 2, "url": "u2", "retrieved_at": "x",
         "posts": [{"text": "Python"}, {"text": "customer success team"}, {"text": "Rust"}, {"text": "python &amp; more"}]},
        {"month": "2026-09", "story_id": 1, "url": "u1", "retrieved_at": "x",
         "posts": [{"text": "<p>Python</p>"}, {"text": "Go"}]},
    ]
    exposure = load_exposure.skill_exposure(SKILLS, EXPOSURE, ONET)
    snap = build_snapshot.assemble(raw, SKILLS, exposure, sources=[{"id": "s"}], retrieved_at="2026-10-20T09:00:00Z")

    assert snap["snapshot_date"] == "2026-10-20"
    assert [m["month"] for m in snap["months"]] == ["2026-09", "2026-10"]  # oldest -> newest
    assert [m["total_posts"] for m in snap["months"]] == [2, 4]
    py = snap["skills"]["python"]
    assert py["counts"] == [1, 2] and py["shares"] == [0.5, 0.5]
    assert py["exposure"] == 0.4 and py["exposure_method"] == "onet_tech"
    assert snap["skills"]["customer_success"]["counts"] == [0, 1]
    assert "is_example" not in snap


# --- refresh (build(refresh_current_only=True)) ---

import json  # noqa: E402

import pytest  # noqa: E402

PREVIOUS = {
    "snapshot_date": "2026-10-01",
    "retrieved_at": "2026-10-01T00:00:00Z",
    "sources": [{"id": "hn_whoishiring", "retrieved_at": "old"}, {"id": "aei_job_exposure", "retrieved_at": "keep"}],
    "months": [{"month": "2026-09", "story_id": 1, "url": "u1", "total_posts": 2},
               {"month": "2026-10", "story_id": 2, "url": "u2", "total_posts": 2}],
    "skills": {
        "python": {"counts": [1, 1], "shares": [0.5, 0.5], "exposure": 0.4, "exposure_n_occupations": 2,
                   "exposure_method": "onet_tech"},
        "customer_success": {"counts": [0, 0], "shares": [0.0, 0.0], "exposure": 0.7, "exposure_n_occupations": 1,
                             "exposure_method": "proxy"},
        "nothing": {"counts": [0, 0], "shares": [0.0, 0.0], "exposure": None, "exposure_n_occupations": 0,
                    "exposure_method": None},
    },
}


def newest(month, story_id, texts):
    return {"month": month, "story_id": story_id, "url": f"u{story_id}", "retrieved_at": "new",
            "posts": [{"text": t} for t in texts]}


def test_refresh_replaces_current_month():
    snap = build_snapshot.refresh_latest(PREVIOUS, newest("2026-10", 2, ["Python", "python", "Rust"]), SKILLS,
                                         "2026-10-21T08:00:00Z")
    assert snap["snapshot_date"] == "2026-10-21"
    assert [m["total_posts"] for m in snap["months"]] == [2, 3]
    assert snap["skills"]["python"]["counts"] == [1, 2] and snap["skills"]["python"]["shares"] == [0.5, 0.6667]
    assert snap["skills"]["python"]["exposure"] == 0.4  # reused, not recomputed
    assert snap["sources"] == [{"id": "hn_whoishiring", "retrieved_at": "new"},
                               {"id": "aei_job_exposure", "retrieved_at": "keep"}]
    assert PREVIOUS["months"][-1]["total_posts"] == 2  # input not mutated


def test_refresh_appends_new_month_and_keeps_window(monkeypatch):
    monkeypatch.setattr(build_snapshot, "MONTHS", 2)
    snap = build_snapshot.refresh_latest(PREVIOUS, newest("2026-11", 3, ["customer success"]), SKILLS, "2026-11-02T00:00:00Z")
    assert [m["month"] for m in snap["months"]] == ["2026-10", "2026-11"]
    assert snap["skills"]["customer_success"]["counts"] == [0, 1]
    assert snap["skills"]["python"]["counts"] == [1, 0]


def test_refresh_rejects_new_skills_and_old_months():
    with pytest.raises(ValueError, match="full rebuild"):
        build_snapshot.refresh_latest(PREVIOUS, newest("2026-10", 2, []),
                                      SKILLS + [{"skill_id": "brand_new", "aliases": ["x"]}], "2026-10-21T00:00:00Z")
    with pytest.raises(ValueError, match="older"):
        build_snapshot.refresh_latest(PREVIOUS, newest("2026-08", 0, []), SKILLS, "2026-10-21T00:00:00Z")


def test_failed_refresh_leaves_snapshot_untouched(monkeypatch, tmp_path):
    (tmp_path / "latest.json").write_text(json.dumps(PREVIOUS), encoding="utf-8")
    monkeypatch.setattr(build_snapshot, "SNAPSHOTS", tmp_path)

    def offline(*args, **kwargs):
        raise OSError("network down")

    monkeypatch.setattr(build_snapshot.fetch_hn, "list_threads", offline)
    with pytest.raises(build_snapshot.RefreshError, match="network down"):
        build_snapshot.build(refresh_current_only=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["latest.json"]
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8")) == PREVIOUS
