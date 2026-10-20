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
