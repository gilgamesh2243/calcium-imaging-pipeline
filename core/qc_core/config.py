"""
Config loader – reads global.yaml → labs/{lab_id}.yaml → rigs/{lab_id}/{rig_id}.yaml
and merges them with deep-merge semantics.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(
    lab_id: str | None = None,
    rig_id: str | None = None,
    config_root: str | Path | None = None,
) -> dict[str, Any]:
    """Load merged config for the given lab/rig."""
    if config_root is None:
        config_root = Path(os.environ.get("QC_CONFIG_ROOT", "configs"))
    root = Path(config_root)

    cfg: dict[str, Any] = {}

    def _load(path: Path) -> None:
        nonlocal cfg
        if path.exists():
            with path.open() as f:
                data = yaml.safe_load(f) or {}
            cfg = _deep_merge(cfg, data)

    _load(root / "global.yaml")
    if lab_id:
        _load(root / "labs" / f"{lab_id}.yaml")
    if lab_id and rig_id:
        _load(root / "rigs" / lab_id / f"{rig_id}.yaml")

    # Environment variable overrides (QC_<KEY>=value, dot-path with __)
    for key, val in os.environ.items():
        if key.startswith("QC_") and key != "QC_CONFIG_ROOT":
            parts = key[3:].lower().split("__")
            node = cfg
            for p in parts[:-1]:
                node = node.setdefault(p, {})
            node[parts[-1]] = val

    return cfg
