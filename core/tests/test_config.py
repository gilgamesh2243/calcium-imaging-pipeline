"""
Tests for config loader.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml
import pytest

from qc_core.config import load_config


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data))


def test_load_global_only(tmp_path):
    _write_yaml(tmp_path / "global.yaml", {"streaming": {"fps": 30}, "qc": {"saturation_threshold_pct": 1.0}})
    cfg = load_config(config_root=tmp_path)
    assert cfg["streaming"]["fps"] == 30
    assert cfg["qc"]["saturation_threshold_pct"] == 1.0


def test_deep_merge(tmp_path):
    _write_yaml(tmp_path / "global.yaml", {"streaming": {"fps": 30, "batch_size": 8}})
    _write_yaml(tmp_path / "labs" / "lab1.yaml", {"streaming": {"fps": 10}})
    cfg = load_config(lab_id="lab1", config_root=tmp_path)
    assert cfg["streaming"]["fps"] == 10
    assert cfg["streaming"]["batch_size"] == 8  # from global, not overridden


def test_missing_files_ok(tmp_path):
    cfg = load_config(lab_id="nonexistent", rig_id="rig99", config_root=tmp_path)
    assert isinstance(cfg, dict)


def test_env_override(tmp_path, monkeypatch):
    _write_yaml(tmp_path / "global.yaml", {"qc": {"saturation_threshold_pct": 1.0}})
    monkeypatch.setenv("QC_QC__SATURATION_THRESHOLD_PCT", "5.0")
    cfg = load_config(config_root=tmp_path)
    assert cfg["qc"]["saturation_threshold_pct"] == "5.0"
