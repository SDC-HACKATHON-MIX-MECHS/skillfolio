"""Skill -> occupations -> AI exposure (SPEC 4.3). Lane B.

Sources:
- Anthropic Economic Index job_exposure.csv (CC-BY):
  https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/labor_market_impacts/job_exposure.csv
  columns: occ_code (e.g. 15-2051), title, observed_exposure
- O*NET 31.0 Technology Skills, inside https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip (CC BY 4.0)
  columns: O*NET-SOC Code (e.g. 15-1252.00), Title, Example, Commodity Code, Commodity Title, Hot Technology, In Demand
"""

from __future__ import annotations

JOB_EXPOSURE_URL = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/labor_market_impacts/job_exposure.csv"
ONET_ZIP_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip"


def download_sources() -> dict:
    """Download both files into data/raw/ and return {source_id: {path, url, licence, retrieved_at}}."""
    raise NotImplementedError("lane B")


def skill_exposure(skills: list[dict], job_exposure: dict[str, float], onet_tech: list[dict]) -> dict[str, dict]:
    """skill_id -> {exposure, exposure_n_occupations, exposure_method}.

    Mean observed_exposure over O*NET occupations whose Technology Skills include any of the
    skill's `onet_examples` (SOC = first 7 chars of the O*NET code). If none, use proxy_soc_codes
    (method 'proxy'). If still none, exposure = None.
    """
    raise NotImplementedError("lane B")


def generate_role_skills(roles: list[dict], skills: list[dict], onet_tech: list[dict]) -> list[dict]:
    """Rows for data/role_skills.generated.csv: In Demand -> weight 3, Hot Technology -> weight 2.
    Lanes A + D curate this into data/role_skills.csv (max 10 skills per role)."""
    raise NotImplementedError("lane B")
