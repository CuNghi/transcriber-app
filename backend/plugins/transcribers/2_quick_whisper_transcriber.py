# backend/plugins/transcribers/quick_whisper_transcriber.py

import os
import sys
from faster_whisper import WhisperModel

_model       = None
_was_offline = False

# map the “model_size” names you expect → your local folder names
_FOLDER_MAP = {
    "tiny":       "whisper-tiny",
    "tiny.en":    "whisper-tiny.en",
    "base":       "whisper-base.en",
    "base.en":    "whisper-base.en",
    "small":      "whisper-small",
    "small.en":   "whisper-small.en",
    "medium":     "whisper-medium",
    "medium.en":  "whisper-medium.en",
    "large-v2":   "whisper-large-v2",
    # add more if you bundle them…
}

def initialize(device: str, model_size: str = "base"):
    """
    Initialize faster-whisper WhisperModel on the given device.
    Default model_size is "base" (i.e. whisper-base.en).
    """
    global _model, _was_offline

    compute_type = "float32" if device == "cpu" else "float16"

    # locate snapshot dir in EXE vs SOURCE
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.getcwd(), "backend")

    folder = _FOLDER_MAP.get(model_size)
    local_dir = os.path.join(base, "models", folder) if folder else None

    if local_dir and os.path.isdir(local_dir):
        _model = WhisperModel(
            local_dir,
            device=device,
            compute_type=compute_type,
            local_files_only=True
        )
        _was_offline = True
        print(f"[✔] quick‐whisper loaded OFFLINE from {local_dir}")
    else:
        _model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        _was_offline = False
        print(f"[!] quick‐whisper loaded ONLINE (no local snapshot at {local_dir})")

def is_offline() -> bool:
    """True if we actually loaded the model from disk."""
    return _was_offline

def transcribe(audio_path: str) -> dict:
    """
    Transcribe the file at audio_path:
      returns {"text": "...", "words": [...]}
    """
    segments, _info = _model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
    )

    words = []
    text_chunks = []
    for seg in segments:
        text_chunks.append(seg.text.strip())
        for w in getattr(seg, "words", []):
            words.append({
                "word":       w.word,
                "start":      w.start,
                "end":        w.end,
                "confidence": getattr(w, "probability", 1.0),
            })

    return {
        "text":  " ".join(text_chunks),
        "words": words,
    }
