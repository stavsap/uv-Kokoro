"""Command line interface for the uv-kokoro TTS tool."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import config, voices
from .config import app_dir, get_mix, load as load_config, save as save_config
from .voices import LANG_LABELS, SEX_LABELS, VoiceSpecError, groups, parse_voice_spec

SAMPLE_RATE = 24000


def _read_text(input_arg: str) -> tuple[str, Path | None]:
    """Read text from a file path or '-' for stdin."""
    if input_arg == "-":
        return sys.stdin.read(), None
    p = Path(input_arg)
    try:
        return p.read_text(encoding="utf-8"), p.resolve()
    except FileNotFoundError as exc:
        raise SystemExit(f"error: input text file not found: {p}") from exc


def _resolve_voice(spec_str, mix_name) -> voices.VoiceSpec:
    """Resolve an explicit spec string, a named mix, or the saved default."""
    if spec_str:
        return parse_voice_spec(spec_str)
    if mix_name:
        saved = get_mix(mix_name)
        if not saved:
            raise SystemExit(f"error: no saved mix named '{mix_name}'.")
        return parse_voice_spec(saved)
    default = config.get_defaults().get("voice")
    if default:
        print(
            f"(using speaker from preferences: {default})", file=sys.stderr
        )
        return parse_voice_spec(default)
    raise SystemExit(
        "error: no speaker selected. Pass --voice, use a named mix via "
        "--mix NAME, or set a default with `uv-kokoro config set voice af_bella`. "
        "Run `uv-kokoro voices` to list speakers."
    )


def _resolve_speed(speed):
    if speed is not None:
        return speed
    try:
        val = float(config.get_defaults().get("speed"))
    except (TypeError, ValueError):
        val = 1.0
    return val


def _resolve_output(output: str | None, input_path: Path | None) -> Path:
    if output:
        out = Path(output).expanduser()
    elif input_path is not None and input_path.suffix.lower() == ".txt":
        out_dir = config.get_defaults().get("output_dir") or "."
        out = Path(out_dir) / f"{input_path.stem}.wav"
    else:
        raise SystemExit(
            "error: please provide an output filename with --output (or -o)."
        )
    if not str(out).lower().endswith(".wav"):
        out = out.with_suffix(".wav")
    return out


def _fmt_duration(samples: int) -> str:
    secs = samples / SAMPLE_RATE
    m, s = divmod(int(round(secs)), 60)
    return f"{m}m{s:02d}s" if m else f"{s}s"


# ---------------------------------------------------------------- commands

def cmd_speak(args):
    from .tts import Synthesizer, write_wav

    text, input_path = _read_text(args.input)
    if not text.strip():
        raise SystemExit("error: no text to synthesize.")

    spec = _resolve_voice(getattr(args, "voice", None), getattr(args, "mix", None))
    try:
        spec.validate()
    except VoiceSpecError as exc:
        raise SystemExit(f"error: {exc}") from exc

    speed = _resolve_speed(getattr(args, "speed", None))
    out_path = _resolve_output(getattr(args, "output", None), input_path)
    device = getattr(args, "device", None) or config.get_defaults().get("device")

    if spec.is_mix:
        print(
            f"Blending {len(spec.names)} speakers: {spec.label}", file=sys.stderr
        )

    syn = Synthesizer(device=device)
    t0 = time.time()
    try:
        audio = syn.synthesize(text, spec, speed=speed)
    except Exception as exc:  # noqa: BLE001 - surface cleanly to the user
        raise SystemExit(f"error during synthesis: {exc}") from exc

    written = write_wav(out_path, audio)

    # Remember what we just used so future invocations default to it.
    cfg = load_config()
    cfg["defaults"]["voice"] = spec.label
    cfg["defaults"]["speed"] = speed
    if device:
        cfg["defaults"]["device"] = device
    save_config(cfg)

    print(
        f"Wrote {written} ({_fmt_duration(len(audio))}, took {time.time() - t0:.1f}s)"
    )


def cmd_voices(args):
    rows = voices.list_voices(lang=args.lang, sex=args.sex)
    if not rows:
        raise SystemExit("error: no speakers match the given filters.")
    print(f"{'Code':<5}{'Sex':<8}Speaker")
    print("-" * 44)
    for lang_code, name in rows:
        label = SEX_LABELS.get(voices.sex_of(name), voices.sex_of(name))
        print(f"{lang_code:<5}{label:<8}{name}")
    if args.lang and args.lang in LANG_LABELS:
        print(f"\n[{args.lang}] {LANG_LABELS[args.lang]}")


def cmd_config(args):
    cfg = load_config()
    if args.action == "show":
        print(f"Preferences file: {config.config_path()}")
        for k, v in cfg["defaults"].items():
            print(f"  {k}: {v}")
        mixes = cfg.get("mixes") or {}
        if mixes:
            print("Mixes:")
            for name, spec_str in mixes.items():
                print(f"  {name}: {spec_str}")
    elif args.action == "set":
        try:
            config.set_pref(args.key, args.value)
        except KeyError as exc:
            raise SystemExit(f"error: {exc}") from exc
        print(f"saved preference {args.key}={args.value}")
    else:  # path
        print(app_dir())


def cmd_mix(args):
    cfg = load_config()
    if args.action == "add":
        spec = parse_voice_spec("+".join(args.speakers))
        try:
            spec.validate()
        except VoiceSpecError as exc:
            raise SystemExit(f"error: {exc}") from exc
        config.set_mix(args.name, spec.label)
        print(f"saved mix '{args.name}' = {spec.label}")
    elif args.action == "remove":
        if not cfg.get("mixes", {}).get(args.name):
            raise SystemExit(f"error: no saved mix named '{args.name}'.")
        del cfg["mixes"][args.name]
        save_config(cfg)
        print(f"removed mix '{args.name}'")
    elif args.action == "list":
        mixes = cfg.get("mixes") or {}
        if not mixes:
            print(
                "No named blends yet. Add one with "
                "`uv-kokoro mix add NAME s1:weight s2:weight`."
            )
            return
        for name, spec_str in sorted(mixes.items()):
            print(f"  {name}: {spec_str}")


# ----------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uv-kokoro",
        description=(
            "Text-to-speech with the Kokoro model: choose a speaker, blend "
            "two speakers together, and render text files to WAV audio."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_speak = sub.add_parser("speak", help="Synthesize speech from a text file.")
    p_speak.add_argument(
        "input", metavar="TEXT_FILE",
        help="Input .txt file (use '-' for stdin).",
    )
    p_speak.add_argument("-o", "--output", help="Output WAV filename.")
    p_speak.add_argument(
        "-v", "--voice",
        help="Speaker(s): 'af_bella', or a blend like "
             "'af_bella+af_nicole:0.7'.",
    )
    p_speak.add_argument("-s", "--speed", type=float, default=None,
                         help="Speech speed (default 1.0).")
    p_speak.add_argument("--device", choices=["cpu", "cuda"], default=None,
                         help="Override compute device.")
    p_speak.add_argument(
        "--mix", metavar="NAME",
        help="Use a previously saved named blend from preferences.",
    )
    p_speak.set_defaults(func=cmd_speak)

    p_voices = sub.add_parser("voices", aliases=["list"],
                              help="List available speakers.")
    p_voices.add_argument(
        "--lang", choices=sorted(LANG_LABELS),
        help="Filter by language code (a, b, e, f, h, i, j, p, z).",
    )
    p_voices.add_argument("--sex", choices=["m", "f"],
                          help="Filter male/female.")
    p_voices.set_defaults(func=cmd_voices)

    p_config = sub.add_parser(
        "config", aliases=["prefs"],
        help="View/edit preferences saved in ~/.uv-kokoro.",
    )
    cfg_sub = p_config.add_subparsers(dest="action", required=True)
    s_show = cfg_sub.add_parser("show")
    s_set = cfg_sub.add_parser(
        "set",
        help="Set a default (voice, speed, device, output_dir).",
    )
    s_path = cfg_sub.add_parser("path")
    for p in (s_show, s_set, s_path):
        p.set_defaults(func=cmd_config)
    s_set.add_argument("key")
    s_set.add_argument("value")

    p_mix = sub.add_parser(
        "mix", aliases=["blend"],
        help="Save/list/remove named speaker blends in preferences.",
    )
    mix_sub = p_mix.add_subparsers(dest="action", required=True)
    m_add = mix_sub.add_parser("add")
    m_add.add_argument("name", help="Name of the blend to save.")
    m_add.add_argument(
        "speakers", nargs="+",
        help="Speakers and weights, e.g. 'af_bella:0.7' 'af_nicole:1'. "
             "(weights are normalized).",
    )
    m_rm = mix_sub.add_parser("remove")
    m_rm.add_argument("name")
    m_list = mix_sub.add_parser("list", help="List saved blends.")
    for p in (m_add, m_rm, m_list):
        p.set_defaults(func=cmd_mix)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
