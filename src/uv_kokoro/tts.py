"""Kokoro interaction: model loading, speaker selection and synthesis."""

from __future__ import annotations

import os
import wave
from pathlib import Path

# Bootstrap espeak-ng data path *before* importing KPipeline.
# When installed via ``uv tool install`` the VIRTUAL_ENV env-var is not
# exported, so misaki / espeakng-loader cannot locate the bundled
# espeak-ng-data directory.  Setting ESPEAK_DATA_PATH explicitly fixes this.
try:
    import espeakng_loader

    os.environ.setdefault("ESPEAK_DATA_PATH", espeakng_loader.get_data_path())
except ImportError:
    pass  # system espeak-ng will be used as fallback

import numpy as np
import torch
from kokoro import KPipeline

REPO_ID = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24000


class Synthesizer:
    """Wraps one or more ``KPipeline`` instances (one per language).

    Reuses the same pipeline across calls so that already-downloaded voices
    and models are kept in memory.
    """

    def __init__(self, device: str | None = None):
        self.device = device
        self._pipes: dict[str, KPipeline] = {}

    def _pipe(self, lang_code: str) -> KPipeline:
        if lang_code not in self._pipes:
            self._pipes[lang_code] = KPipeline(
                lang_code=lang_code,
                repo_id=REPO_ID,
                model=True,
                device=self.device,
            )
        return self._pipes[lang_code]

    def voice_for(self, spec):
        """Return a voice value suitable for ``KPipeline.__call__``.

        A single speaker is passed through by name (letting the pipeline cache
        it). Multiple speakers are blended into a raw tensor with normalized
        weights. Passing a tensor to KPipeline works because it moves the pack
        onto the model device itself.
        """
        if not spec.is_mix:
            return spec.names[0]
        pipe = self._pipe(spec.lang())
        packs = [pipe.load_single_voice(name) for name in spec.names]
        weights = torch.tensor(
            [w for _, w in spec.pairs], dtype=packs[0].dtype
        )
        # Normalize so the blend ratio reads intuitively (e.g. a:2 + b:1 == 2/3, 1/3).
        if len(weights) > 0:
            weights = weights / weights.sum()
        mixed = torch.zeros_like(packs[0])
        for pack, w in zip(packs, weights):
            mixed += pack * w
        return mixed

    def synthesize(self, text: str, spec, speed: float = 1.0) -> np.ndarray:
        """Run TTS and return the full mono audio as a float32 numpy array."""
        pipe = self._pipe(spec.lang())
        voice = self.voice_for(spec)
        chunks: list[torch.Tensor] = []
        for result in pipe(text, voice=voice, speed=speed):
            if result.output is not None:
                chunk = result.audio.detach().cpu()
                if chunk.ndim > 1:  # safety flatten
                    chunk = chunk.squeeze(0)
                chunks.append(chunk)
        audio = torch.cat(chunks) if chunks else torch.zeros(
            0, dtype=torch.float32
        )
        return audio.numpy()


def write_wav(path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE):
    """Write a mono float array in [-1, 1] to a PCM16 WAV file."""
    path = Path(path)
    if path.suffix.lower() != ".wav":
        path = path.with_suffix(".wav")
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return path
