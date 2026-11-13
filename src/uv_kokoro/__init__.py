"""uv-kokoro: a uv-installable CLI for Kokoro text-to-speech."""

from .voices import VoiceSpec, parse_voice_spec
from .tts import Synthesizer

__version__ = "0.1.0"
__all__ = ["Synthesizer", "VoiceSpec", "parse_voice_spec", "__version__"]
