"""Shared test setup: no test may reach RunPod, even when a developer has real keys in .env or the environment.
Tests that need the endpoint 'on' replace app.runpod_client.settings / suggest_skills themselves."""

import pytest


@pytest.fixture(autouse=True)
def _runpod_off(monkeypatch, tmp_path):
    from app import runpod_client
    monkeypatch.setattr(runpod_client, "ENV_FILE", tmp_path / "no.env")
    for key in runpod_client.KEYS:
        monkeypatch.delenv(key, raising=False)
