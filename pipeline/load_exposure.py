"""Skill -> occupations -> AI exposure (SPEC 4.3). Lane B.

Sources:
- Anthropic Economic Index job_exposure.csv (CC-BY):
  https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/labor_market_impacts/job_exposure.csv
  columns: occ_code (e.g. 15-2051), title, observed_exposure
- O*NET 31.0 Technology Skills, inside https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip (CC BY 4.0)
  columns: O*NET-SOC Code (e.g. 15-1252.00), Title, Example, Commodity Code, Commodity Title, Hot Technology, In Demand
  (31.0 ships it as software_skills.csv with 'Workplace Example', 'Element ID', 'Element Name'; see read_onet_tech)

Run:  python -m pipeline.load_exposure            # download if missing, write role_skills.generated.csv
      python -m pipeline.load_exposure --force    # re-download both files
"""

from __future__ import annotations

import csv
import io
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

JOB_EXPOSURE_URL = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/labor_market_impacts/job_exposure.csv"
ONET_ZIP_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip"

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ROLE_SKILLS_GENERATED = ROOT / "data" / "role_skills.generated.csv"
SOURCES_META = RAW / "sources.json"  # retrieval times of the cached downloads

SOURCES = {
    "aei_job_exposure": {
        "name": "Anthropic Economic Index — job_exposure.csv",
        "url": "https://huggingface.co/datasets/Anthropic/EconomicIndex",
        "download_url": JOB_EXPOSURE_URL,
        "licence": "CC-BY",
        "file": "job_exposure.csv",
    },
    "onet_tech": {
        "name": "O*NET 31.0 Technology Skills",
        "url": "https://www.onetcenter.org/database.html",
        "download_url": ONET_ZIP_URL,
        "licence": "CC BY 4.0",
        "file": "onet_db_31_0_csv.zip",
    },
}
# File name inside the O*NET zip: 31.0 uses software_skills.csv; older releases "Technology Skills.txt".
ONET_TECH_MEMBERS = ("software_skills.csv", "Technology Skills.txt")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def download_sources(force: bool = False) -> dict:
    """Download both files into data/raw/ and return {source_id: {path, url, licence, retrieved_at}}."""
    RAW.mkdir(parents=True, exist_ok=True)
    meta = json.loads(SOURCES_META.read_text(encoding="utf-8")) if SOURCES_META.exists() else {}
    out = {}
    for source_id, src in SOURCES.items():
        path = RAW / src["file"]
        if force or not path.exists() or source_id not in meta:
            req = urllib.request.Request(src["download_url"], headers={"User-Agent": "skillfolio-hackathon/0.1"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                path.write_bytes(resp.read())
            meta[source_id] = _now_iso()
            print(f"downloaded {source_id} -> {path.relative_to(ROOT)}")
        out[source_id] = {
            "id": source_id,
            "name": src["name"],
            "path": str(path),
            "url": src["url"],
            "licence": src["licence"],
            "retrieved_at": meta[source_id],
        }
    SOURCES_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out


def read_job_exposure(path: str | Path) -> dict[str, float]:
    """{occ_code: observed_exposure} from job_exposure.csv."""
    with open(path, newline="", encoding="utf-8") as f:
        return {r["occ_code"]: float(r["observed_exposure"]) for r in csv.DictReader(f) if r["observed_exposure"]}


def read_onet_tech(zip_path: str | Path) -> list[dict]:
    """Rows of the O*NET Technology Skills file inside the zip.

    O*NET 31.0 (Aug 2026) renamed the file to software_skills.csv and the 'Example' column to
    'Workplace Example'; rows are normalised so they always have an 'Example' key.
    """
    with zipfile.ZipFile(zip_path) as z:
        member = next(n for n in z.namelist() if n.endswith(ONET_TECH_MEMBERS))
        with z.open(member) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig")
            rows = list(csv.DictReader(text, delimiter="\t" if member.endswith(".txt") else ","))
    for row in rows:
        row.setdefault("Example", row.get("Workplace Example", ""))
    return rows


def _soc(onet_code: str) -> str:
    return onet_code[:7]  # 15-1252.00 -> 15-1252


def skill_exposure(skills: list[dict], job_exposure: dict[str, float], onet_tech: list[dict]) -> dict[str, dict]:
    """skill_id -> {exposure, exposure_n_occupations, exposure_method}.

    Mean observed_exposure over O*NET occupations whose Technology Skills include any of the
    skill's `onet_examples` (SOC = first 7 chars of the O*NET code). If none, use proxy_soc_codes
    (method 'proxy'). If still none, exposure = None.
    """
    socs_by_example: dict[str, set[str]] = {}
    for row in onet_tech:
        socs_by_example.setdefault(row["Example"], set()).add(_soc(row["O*NET-SOC Code"]))

    out = {}
    for s in skills:
        socs = set().union(*(socs_by_example.get(ex, set()) for ex in s["onet_examples"]))
        values = [job_exposure[soc] for soc in socs if soc in job_exposure]
        method = "onet_tech"
        if not values:
            values = [job_exposure[soc] for soc in s["proxy_soc_codes"] if soc in job_exposure]
            method = "proxy"
        if values:
            out[s["skill_id"]] = {
                "exposure": round(mean(values), 4),
                "exposure_n_occupations": len(values),
                "exposure_method": method,
            }
        else:
            out[s["skill_id"]] = {"exposure": None, "exposure_n_occupations": 0, "exposure_method": None}
    return out


def generate_role_skills(roles: list[dict], skills: list[dict], onet_tech: list[dict]) -> list[dict]:
    """Rows for data/role_skills.generated.csv: In Demand -> weight 3, Hot Technology -> weight 2.
    Lanes A + D curate this into data/role_skills.csv (max 10 skills per role)."""
    skill_by_example = {ex: s["skill_id"] for s in skills for ex in s["onet_examples"]}
    best: dict[tuple[str, str], tuple[int, str]] = {}
    for role in roles:
        for row in onet_tech:
            if _soc(row["O*NET-SOC Code"]) != role["soc_code"]:
                continue
            skill_id = skill_by_example.get(row["Example"])
            if not skill_id:
                continue
            if row.get("In Demand") == "Y":
                weight, source = 3, "onet_in_demand"
            elif row.get("Hot Technology") == "Y":
                weight, source = 2, "onet_hot"
            else:
                continue
            key = (role["role_id"], skill_id)
            if key not in best or weight > best[key][0]:
                best[key] = (weight, source)
    return [
        {"role_id": r, "skill_id": s, "weight": w, "required_level": 2, "source": src}
        for (r, s), (w, src) in sorted(best.items(), key=lambda kv: (kv[0][0], -kv[1][0], kv[0][1]))
    ]


def write_role_skills_generated(rows: list[dict], path: Path = ROLE_SKILLS_GENERATED) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["role_id", "skill_id", "weight", "required_level", "source"])
        writer.writeheader()
        writer.writerows(rows)
    return path


if __name__ == "__main__":
    import sys

    from engine.data import load_roles, load_skills

    sources = download_sources(force="--force" in sys.argv)
    skills = load_skills()
    exposure = read_job_exposure(sources["aei_job_exposure"]["path"])
    onet = read_onet_tech(sources["onet_tech"]["path"])

    by_skill = skill_exposure(skills, exposure, onet)
    missing = [k for k, v in by_skill.items() if v["exposure"] is None]
    print(f"{len(by_skill) - len(missing)}/{len(by_skill)} skills have exposure; missing: {', '.join(missing) or 'none'}")

    rows = generate_role_skills(load_roles(), skills, onet)
    print(f"wrote {len(rows)} rows to {write_role_skills_generated(rows).relative_to(ROOT)}")
