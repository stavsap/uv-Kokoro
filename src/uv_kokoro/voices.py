"""Speaker metadata for the Kokoro-82M voice set.

Kokoro voice names are structured as ``XY_name`` where:

* ``X`` is the language code (a, b, e, f, h, i, j, p, z)
* ``Y`` is the sex of the voice (m = male, f = female)

The actual audio weights live on HuggingFace in the
``hexgrad/Kokoro-82M`` repo under ``voices/{name}.pt``.
"""

# Full list of speakers shipped with Kokoro-82M.
VOICE_NAMES: tuple[str, ...] = (
    "af_alloy", "af_aoede", "af_bella", "af_heart",
    "af_jessica", "af_kore", "af_nicole", "af_nova",
    "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir",
    "am_liam", "am_michael", "am_onyx", "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    "ef_dora", "em_alex", "em_santa",
    "ff_siwis",
    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    "if_sara", "im_nicola",
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
    "pf_dora", "pm_alex", "pm_santa",
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
)

# Language code -> human readable label, matching KPipeline.LANG_CODES.
LANG_LABELS: dict[str, str] = {
    "a": "American English",
    "b": "British English",
    "e": "Spanish (es)",
    "f": "French",
    "h": "Hindi",
    "i": "Italian",
    "j": "Japanese",
    "p": "Portuguese (Brazil)",
    "z": "Mandarin Chinese",
}

SEX_LABELS: dict[str, str] = {
    "m": "male",
    "f": "female",
}


def lang_of(name: str) -> str:
    """Return the language code of a voice name (its first character)."""
    return name[0]


def sex_of(name: str) -> str:
    """Return 'm' or 'f' for a voice name (its second character)."""
    return name[1]


class VoiceSpecError(ValueError):
    pass


class VoiceSpec:
    """A resolved list of ``(name, weight)`` pairs describing how to blend voices."""

    def __init__(self, pairs: list[tuple[str, float]]):
        self.pairs = [(n, w) for n, w in pairs]

    @property
    def names(self) -> list[str]:
        return [n for n, _ in self.pairs]

    @property
    def is_mix(self) -> bool:
        return len(self.names) > 1

    def validate(self):
        """Ensure every speaker exists and the mix shares one language."""
        if not self.names:
            raise VoiceSpecError("No speakers were selected.")
        for name in self.names:
            if name not in VOICE_NAMES:
                known = ", ".join(VOICE_NAMES)
                raise VoiceSpecError(
                    f"Unknown speaker '{name}'. "
                    f"Run `uv-kokoro voices` to see all options.\n"
                    f"Known speakers: {known}"
                )
        langs = {lang_of(n) for n in self.names}
        if len(langs) > 1:
            raise VoiceSpecError(
                "Mixed speakers must share a language. "
                f"Got languages: {', '.join(sorted(LANG_LABELS.get(l, l) for l in langs))}"
            )

    def lang(self) -> str:
        return lang_of(self.names[0])

    @property
    def label(self) -> str:
        if not self.is_mix:
            return self.names[0]
        parts = [f"{n}:{w:g}" for n, w in self.pairs]
        return "+".join(parts)

    def __str__(self):
        return f"<VoiceSpec {self.label}>"


def parse_voice_spec(spec: str) -> VoiceSpec:
    """Parse a voice specification string.

    Supported syntax:

    * ``af_bella``                          single speaker
    * ``af_bella,af_jessica``               equal-weight blend
    * ``af_bella+af_nicole:0.7``            weighted blend (weights are normalized)
    """
    parts = __import__("re").split(r"[+,]", spec)
    pairs: list[tuple[str, float]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, _, weight_s = part.rpartition(":")
            try:
                weight = float(weight_s)
            except ValueError as exc:  # pragma: no cover - trivial guard
                raise VoiceSpecError(f"Invalid weight '{weight_s}' in '{part}'.") from exc
        else:
            name, weight = part, 1.0
        pairs.append((name.strip(), weight))
    return VoiceSpec(pairs)


def list_voices(lang: str | None = None, sex: str | None = None):
    """Return voices as (lang_code, name) tuples, optionally filtered."""
    result = []
    for name in VOICE_NAMES:
        if lang is not None and lang_of(name) != lang:
            continue
        if sex is not None and sex_of(name) != sex:
            continue
        result.append((lang_of(name), name))
    return result


def groups():
    """Return voices grouped by language, for pretty printing."""
    out = {}
    for name in VOICE_NAMES:
        out.setdefault(lang_of(name), []).append(name)
    return {k: v for k, v in sorted(out.items())}
