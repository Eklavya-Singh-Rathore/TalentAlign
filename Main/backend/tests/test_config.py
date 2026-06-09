"""Tests for app.core.config, incl. the P3.1 env-var rename shim."""

from __future__ import annotations

import pytest

from app.core import config as cfg


class TestWeightConfigPathShim:
    """TALENTALIGN_WEIGHT_CONFIG_PATH is read first; the legacy
    CPPS_WEIGHT_CONFIG_PATH is still honored (deprecated) for back-compat."""

    def test_new_var_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("TALENTALIGN_WEIGHT_CONFIG_PATH", "/new/path.json")
        monkeypatch.setenv("CPPS_WEIGHT_CONFIG_PATH", "/legacy/path.json")
        assert cfg._resolve_config_path_from_env() == "/new/path.json"

    def test_legacy_var_still_works(self, monkeypatch):
        monkeypatch.delenv("TALENTALIGN_WEIGHT_CONFIG_PATH", raising=False)
        monkeypatch.setenv("CPPS_WEIGHT_CONFIG_PATH", "/legacy/path.json")
        assert cfg._resolve_config_path_from_env() == "/legacy/path.json"

    def test_legacy_var_logs_deprecation(self, monkeypatch, caplog):
        import logging
        monkeypatch.delenv("TALENTALIGN_WEIGHT_CONFIG_PATH", raising=False)
        monkeypatch.setenv("CPPS_WEIGHT_CONFIG_PATH", "/legacy/path.json")
        with caplog.at_level(logging.WARNING):
            cfg._resolve_config_path_from_env()
        assert any("deprecated" in r.message.lower() for r in caplog.records)

    def test_default_when_neither_set(self, monkeypatch):
        monkeypatch.delenv("TALENTALIGN_WEIGHT_CONFIG_PATH", raising=False)
        monkeypatch.delenv("CPPS_WEIGHT_CONFIG_PATH", raising=False)
        resolved = cfg._resolve_config_path_from_env()
        assert resolved.endswith("weight_config.json")


class TestLoadWeightConfig:
    def test_loads_bundled_config(self, monkeypatch):
        monkeypatch.delenv("TALENTALIGN_WEIGHT_CONFIG_PATH", raising=False)
        monkeypatch.delenv("CPPS_WEIGHT_CONFIG_PATH", raising=False)
        cfg.reset_weight_config_cache()
        wc = cfg.load_weight_config()
        assert wc.profiles  # at least one profile loaded
        # Default profile resolves
        prof = wc.get_profile(wc.default_profile)
        assert prof is not None
