"""Preferences stored in ``~/.uv-kokoro``.

Layout::

    ~/.uv-kokoro/
        config.json   # defaults + named speaker mixes

The ``config.json`` file holds two top-level keys:

* ``defaults`` - the settings used when CLI options are omitted.
  Keys: ``voice``, ``speed``, ``device``, ``output_dir``
* ``mixes``    - a dict of name -> voice-spec-string for reusable blends.

Writes are atomic (write to temp file then rename) so interrupted runs never
corrupt the preferences.
"""

from __future__ import annotations

import json
import os
import tempfile

APP_DIR = os.path.expanduser("~/.uv-kokoro")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

DEFAULTS_TEMPLATE: dict = {
    "defaults": {
        "voice": None,
        "speed": 1.0,
        "device": None,
        "output_dir": None,
    },
    "mixes": {},
}


def app_dir() -> str:
    return APP_DIR


def config_path() -> str:
    return CONFIG_FILE


def _deep_copy(obj):
    return json.loads(json.dumps(obj))


def load() -> dict:
    """Load the full preferences dict, merging in missing template keys."""
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"Could not read preferences file {CONFIG_FILE}: {exc}"
            ) from exc

    cfg = _deep_copy(DEFAULTS_TEMPLATE)
    for section in ("defaults", "mixes"):
        if isinstance(data.get(section), dict):
            cfg[section].update(data[section])
    return cfg


def save(cfg: dict) -> None:
    """Atomically write the preferences file."""
    os.makedirs(APP_DIR, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=APP_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(cfg, fh, indent=2)
            fh.write("\n")
        os.replace(tmp_path, CONFIG_FILE)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def get_defaults() -> dict:
    return load()["defaults"]


def set_pref(key: str, value) -> None:
    """Set a single key inside the ``defaults`` section."""
    cfg = load()
    if key not in DEFAULTS_TEMPLATE["defaults"]:
        raise KeyError(
            f"Unknown preference '{key}'. "
            f"Valid keys: {', '.join(DEFAULTS_TEMPLATE['defaults'])}"
        )
    cfg["defaults"][key] = value
    save(cfg)


def get_mix(name: str) -> str | None:
    return load()["mixes"].get(name)


def set_mix(name: str, voice_spec: str) -> None:
    """Store a named speaker mix."""
    cfg = load()
    cfg["mixes"][name] = voice_spec
    save(cfg)
