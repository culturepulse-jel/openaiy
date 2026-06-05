"""OpenAI-powered speech-to-text, language model, and text-to-speech.

Everything runs through the OpenAI API, so the whole kit needs just one secret:
the OPENAI_API_KEY environment variable. A single shared client is reused for
all three stages.

Interfaces:
    stt.transcribe(wav_path)        -> str
    llm.chat(messages)              -> str   # messages = OpenAI-style list of dicts
    tts.synthesize(text, wav_path)  -> None  # writes a playable .wav
"""

from openai import OpenAI

_client = None


def _get_client():
    """Create the OpenAI client lazily and reuse it (reads OPENAI_API_KEY)."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


class SpeechToText:
    def __init__(self, cfg):
        self.model = cfg.get("model", "whisper-1")

    def transcribe(self, wav_path):
        with open(wav_path, "rb") as f:
            r = _get_client().audio.transcriptions.create(model=self.model, file=f)
        return r.text.strip()


class LanguageModel:
    def __init__(self, cfg):
        self.model = cfg.get("model", "gpt-4o-mini")

    def chat(self, messages):
        r = _get_client().chat.completions.create(model=self.model, messages=messages)
        return r.choices[0].message.content.strip()


class TextToSpeech:
    def __init__(self, cfg):
        self.model = cfg.get("model", "tts-1")
        self.voice = cfg.get("voice", "alloy")

    def synthesize(self, text, wav_path):
        with _get_client().audio.speech.with_streaming_response.create(
            model=self.model, voice=self.voice, input=text, response_format="wav"
        ) as resp:
            resp.stream_to_file(wav_path)


def build_stt(cfg):
    return SpeechToText(cfg)


def build_llm(cfg):
    return LanguageModel(cfg)


def build_tts(cfg):
    return TextToSpeech(cfg)
