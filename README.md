# uv-kokoro

A [uv](https://docs.astral.sh/uv/) installable command line tool for
text-to-speech using the **[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)**
model.

You can:

* choose a speaker from the 54 built-in Kokoro voices,
* **mix two (or more) speakers** together, with custom weights,
* feed it a `.txt` file and get back a `.wav` output file,
* save your preferences to `~/.uv-kokoro/config.json`.

## Installation

Install directly from this project folder:

```bash
cd uv-Kokoro
uv tool install .
```

> Note: Kokoro requires Python `>=3.10, <3.13`. Make sure `uv` uses a
> compatible interpreter (it will pick one automatically if available).

Run it as:

```bash
uv-kokoro --help
```

## Quick start

### List speakers

```bash
uv-kokoro voices                # all 54 voices grouped by language
uv-kokoro voices --lang a       # American English only
uv-kokoro voices --sex f        # female voices only
```

Voice names look like `af_bella`. The first letter is the language code, the
second is the sex:

| Code | Language          |
|------|-------------------|
| a    | American English  |
| b    | British English   |
| e    | Spanish           |
| f    | French            |
| h    | Hindi             |
| i    | Italian           |
| j    | Japanese          |
| p    | Portuguese (BR)   |
| z    | Mandarin Chinese  |

### Synthesize a text file

```bash
uv-kokoro speak notes.txt --voice af_bella -o hello.wav
```

If you omit `--output`, it writes `<input-stem>.wav` next to the input file.
You can read from stdin with `-` as the input:

```bash
echo "Hello world" | uv-kokoro speak - --voice am_liam -o out.wav
```

### Mix two speakers

Mix by listing them, optionally adding weights (weights are normalized):

```bash
# 50 / 50 blend:
uv-kokoro speak notes.txt --voice 'af_bella+af_nicole' -o mix.wav

# weighted blend (~70% af_bella, ~30% af_nicole):
uv-kokoro speak notes.txt --voice 'af_bella:0.7+af_nicole:1' -o mix.wav
```

Speakers in a single mix must share the same language (same first letter).

### Save reusable blends

```bash
# save a named blend to ~/.uv-kokoro/config.json
uv-kokoro mix add myblend af_bella:0.7 af_nicole:1
uv-kokoro speak notes.txt --mix myblend -o out.wav

uv-kokoro mix list       # show saved blends
uv-kokoro mix remove myblend   # delete one
```

### Preferences (`~/.uv-kokoro`)

Preferences are stored in `~/.uv-kokoro/config.json`. The last settings you
used for a successful run (speaker, speed) are remembered automatically.

```bash
uv-kokoro config show                 # print current preferences
uv-kokoro config path                 # print the preferences directory
uv-kokoro config set voice af_bella   # set the default speaker
uv-kokoro config set speed 1.2        # set the default speed
```

## Other options

```bash
# control speech rate and compute device
uv-kokoro speak notes.txt --voice bf_emma --speed 0.9 -o out.wav
uv-kokoro speak notes.txt --voice af_bella --device cpu -o out.wav   # force CPU
```

## Notes

* On first run the Kokoro model (~330 MB) and any requested voice packs are
  downloaded from HuggingFace automatically.
* Audio is written as mono, 24 kHz PCM16 WAV.

## Development

```bash
uv sync                  # create an environment with kokoro installed
uv run uv-kokoro voices
```
