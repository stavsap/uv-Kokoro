"""uv-kokoro: a uv-installable CLI for Kokoro text-to-speech."""

__version__ = "0.1.0"


def __getattr__(name: str):
    """Lazy-load heavy symbols so that ``import uv_kokoro`` stays fast.

    ``torch``, ``numpy`` and ``kokoro`` are only imported when someone
    actually accesses :class:`Synthesizer`, :class:`VoiceSpec`, or
    :func:`parse_voice_spec` on this module.
    """
    if name == "Synthesizer":
        from .tts import Synthesizer

        return Synthesizer
    if name in ("VoiceSpec", "parse_voice_spec"):
        from .voices import VoiceSpec, parse_voice_spec

        return VoiceSpec if name == "VoiceSpec" else parse_voice_spec
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Synthesizer", "VoiceSpec", "parse_voice_spec", "__version__"]
