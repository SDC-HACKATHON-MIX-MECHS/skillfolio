"""app/runpod_client.py: calls the RunPod endpoint, and on ANY problem returns None so the app falls back to keyword matching.
No network: the two HTTP helpers are replaced in every test."""

import pytest

from app import runpod_client as rc
from app.skill_descriptions import DESCRIPTIONS

CATALOG = [{"skill_id": "powerbi", "name": "Power BI", "aliases": ["power bi"], "onet_examples": ["Microsoft Power BI"]},
           {"skill_id": "sql", "name": "SQL", "aliases": ["sql"], "onet_examples": []},
           {"skill_id": "excel", "name": "Excel", "aliases": ["excel"], "onet_examples": []}]
ENV = {"RUNPOD_API_KEY": "k", "RUNPOD_ENDPOINT_ID": "ep"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network call in a test")
    monkeypatch.setattr(rc, "_post", boom)
    monkeypatch.setattr(rc, "_get", boom)


def done(matches):
    return {"status": "COMPLETED", "output": {"matches": matches, "model": "m"}}


def test_not_configured_without_both_keys():
    assert not rc.configured({}) and not rc.configured({"RUNPOD_API_KEY": "k"}) and rc.configured(ENV)


def test_unconfigured_returns_none_without_calling_anything():
    assert rc.suggest_skills("SQL", CATALOG, env={}) is None


def test_skill_texts_describe_the_work_and_fall_back_to_name_and_aliases():
    texts = rc.skill_texts(CATALOG + [{"skill_id": "new_one", "name": "New", "aliases": ["nw"]}])
    assert texts[0] == {"skill_id": "powerbi", "text": DESCRIPTIONS["powerbi"]}
    assert texts[-1] == {"skill_id": "new_one", "text": "New. nw"}


def test_every_catalogue_skill_has_a_description_and_no_extras():
    from engine.data import load_skills
    assert set(DESCRIPTIONS) == {s["skill_id"] for s in load_skills()}


def test_returns_known_ids_best_first_and_drops_unknown_ones(monkeypatch):
    monkeypatch.setattr(rc, "_post", lambda url, payload, headers, timeout: done(
        [{"skill_id": "excel", "score": 0.8}, {"skill_id": "made_up", "score": 0.9}, {"skill_id": "sql", "score": 0.7}]))
    assert rc.suggest_skills("text", CATALOG, env=ENV) == ["excel", "sql"]


def test_the_request_goes_to_runsync_with_the_key_and_the_catalog(monkeypatch):
    seen = {}

    def post(url, payload, headers, timeout):
        seen.update(url=url, payload=payload, headers=headers)
        return done([])
    monkeypatch.setattr(rc, "_post", post)
    rc.suggest_skills("resume text", CATALOG, env=ENV)
    assert seen["url"] == "https://api.runpod.ai/v2/ep/runsync" and seen["headers"]["Authorization"] == "Bearer k"
    assert seen["payload"]["input"]["task"] == "match_skills" and seen["payload"]["input"]["text"] == "resume text"
    assert [s["skill_id"] for s in seen["payload"]["input"]["skills"]] == ["powerbi", "sql", "excel"]


def test_polls_status_while_the_job_is_still_running(monkeypatch):
    monkeypatch.setattr(rc, "_post", lambda *a, **k: {"id": "job1", "status": "IN_QUEUE"})
    answers = iter([{"status": "IN_PROGRESS"}, done([{"skill_id": "sql", "score": 0.7}])])
    urls = []
    monkeypatch.setattr(rc, "_get", lambda url, headers, timeout: urls.append(url) or next(answers))
    monkeypatch.setattr(rc, "_sleep", lambda s: None)
    assert rc.suggest_skills("text", CATALOG, env=ENV) == ["sql"]
    assert urls[0] == "https://api.runpod.ai/v2/ep/status/job1"


def test_gives_up_after_the_deadline(monkeypatch):
    monkeypatch.setattr(rc, "_post", lambda *a, **k: {"id": "job1", "status": "IN_QUEUE"})
    monkeypatch.setattr(rc, "_get", lambda *a, **k: {"status": "IN_QUEUE"})
    clock = iter(range(0, 1000, 10))
    monkeypatch.setattr(rc, "_now", lambda: next(clock))
    monkeypatch.setattr(rc, "_sleep", lambda s: None)
    assert rc.suggest_skills("text", CATALOG, env=ENV) is None


@pytest.mark.parametrize("reply", [
    {"status": "FAILED", "error": "boom"}, {"status": "COMPLETED", "output": {"error": "bad input"}},
    {"status": "COMPLETED", "output": None}, {"status": "COMPLETED", "output": {"matches": "nope"}}, "not a dict", None,
])
def test_bad_replies_give_none(monkeypatch, reply):
    monkeypatch.setattr(rc, "_post", lambda *a, **k: reply)
    assert rc.suggest_skills("text", CATALOG, env=ENV) is None


def test_network_errors_give_none(monkeypatch):
    def fail(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(rc, "_post", fail)
    assert rc.suggest_skills("text", CATALOG, env=ENV) is None


def test_empty_text_is_not_sent(monkeypatch):
    assert rc.suggest_skills("   ", CATALOG, env=ENV) == []


def test_keys_are_read_from_a_local_env_file_when_not_in_the_environment(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# comment\nRUNPOD_API_KEY="k2"\nRUNPOD_ENDPOINT_ID=ep2\n', encoding="utf-8")
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    monkeypatch.delenv("RUNPOD_ENDPOINT_ID", raising=False)
    monkeypatch.setattr(rc, "ENV_FILE", f)
    env = rc.settings()
    assert env["RUNPOD_API_KEY"] == "k2" and env["RUNPOD_ENDPOINT_ID"] == "ep2" and rc.configured(env)


def test_real_environment_wins_over_the_env_file(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("RUNPOD_API_KEY=file\nRUNPOD_ENDPOINT_ID=file\n", encoding="utf-8")
    monkeypatch.setattr(rc, "ENV_FILE", f)
    monkeypatch.setenv("RUNPOD_API_KEY", "real")
    assert rc.settings()["RUNPOD_API_KEY"] == "real"
