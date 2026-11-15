# AGENTS.md

Instructions for AI coding agents working on this project.

## Project overview

**uv-kokoro** is a `uv tool install`-able CLI for text-to-speech using the
[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) model. It wraps the
`kokoro` Python library behind a user-friendly command line with speaker
selection, voice blending, preferences, and WAV output.

## Repository layout

```
pyproject.toml              # Package metadata, dependencies, entry point
src/uv_kokoro/
├── __init__.py             # Public API (lazy-loaded to avoid slow torch import)
├── __main__.py             # `python -m uv_kokoro` entry
├── cli.py                  # argparse CLI — subcommands: speak, voices, config, mix
├── config.py               # Preferences in ~/.uv-kokoro/config.json
├── tts.py                  # Synthesizer, WAV writer, torch/kokoro imports
└── voices.py               # Speaker metadata, VoiceSpec parsing, validation
```

## Key constraints

### Import performance

`torch`, `numpy`, and `kokoro` take several seconds to import. **Never import
them at module level in `cli.py` or `__init__.py`.** They are lazy-loaded so
that lightweight subcommands (`voices`, `config`, `mix`) start instantly. Heavy
imports live in `tts.py` and are only triggered when `cmd_speak` runs.

### uv tool install compatibility

This package is designed to work when installed via `uv tool install`. Keep
these points in mind:

- **`VIRTUAL_ENV` is not set** in uv tool environments. The espeak-ng data
  path bootstrap in `tts.py` (`os.environ.setdefault("ESPEAK_DATA_PATH", ...)`)
  must stay — it fixes espeak-ng discovery for `misaki`.
- **Runtime `pip install` / `spacy download` goes to the wrong env.** That is
  why `en-core-web-sm` is declared as a direct URL dependency in
  `pyproject.toml` rather than downloaded at runtime.
- **`tool.hatch.metadata.allow-direct-references`** must remain `true` for the
  spacy model URL dependency to build.

### Dependencies

| Package | Why |
|---------|-----|
| `kokoro>=0.9.4` | Core TTS model |
| `misaki[en]>=0.9.3` | English G2P (grapheme-to-phoneme), installs `espeakng-loader` |
| `en-core-web-sm` (direct URL) | Spacy model required by misaki — must be a declared dep, not runtime-downloaded |

When updating the spacy model version, ensure it matches the `spacy` version
pulled by `misaki[en]`.

### Audio output

Kokoro generates mono 24 kHz float32 audio. The `write_wav` function converts
to PCM16 WAV. A `--stereo` flag duplicates mono to both channels. Do not
resample.

## Build & test

```bash
uv sync                      # Create dev environment
uv run uv-kokoro voices      # Quick smoke test
uv run uv-kokoro speak test.txt --voice af_bella -o test.wav
```

To test as an installed tool:

```bash
uv tool install --force .
uv-kokoro --help
```

## Style

- Python 3.10+ syntax (`X | Y` unions in annotations behind
  `from __future__ import annotations`).
- No third-party dev dependencies yet (no pytest, ruff, etc.).
- Keep `cli.py` self-contained — all argparse wiring in `build_parser()`.
- Preferences use atomic writes (temp file + `os.replace`).

## Adding a new subcommand

1. Write `cmd_foo(args)` in `cli.py`.
2. Add a subparser in `build_parser()` with `.set_defaults(func=cmd_foo)`.
3. If the command needs torch/kokoro, import inside the function body, not at
   the top of the file.
