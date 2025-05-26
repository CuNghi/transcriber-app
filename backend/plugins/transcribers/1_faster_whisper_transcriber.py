# backend/plugins/transcribers/1_faster_whisper_transcriber.py

import os
import sys
from faster_whisper import WhisperModel

_model       = None
_was_offline = False

def initialize(device: str, model_size: str = "medium"):
    """
    Initialize WhisperModel on given device.
    Tries to load from bundled snapshot at:
       [EXE]   sys._MEIPASS/models/whisper-medium
       [SOURCE] cwd()/backend/models/whisper-medium
    Falls back to HF hub if missing.
    """
    global _model, _was_offline

    compute_type = "float32" if device == "cpu" else "float16"

    # --- locate our local snapshot directory ---
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.getcwd(), "backend")

    folder   = f"whisper-{model_size}"
    local_dir = os.path.join(base, "models", folder)

    if os.path.isdir(local_dir):
        # load offline
        _model       = WhisperModel(
            local_dir,
            device=device,
            compute_type=compute_type,
            local_files_only=True
        )
        _was_offline = True
        print(f"[✔] WhisperModel loaded OFFLINE from {local_dir}")
    else:
        # fall back to online
        _model       = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        _was_offline = False
        print(f"[!] WhisperModel loaded ONLINE (no local snapshot at {local_dir})")

def is_offline() -> bool:
    """True if we actually loaded the model from disk."""
    return _was_offline

def transcribe(path: str) -> dict:
    """
    Run transcription on `path` and return
      { "text": "...", "words": [ {word,start,end,confidence}, … ] }
    """
    segments, _ = _model.transcribe(
        path,
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
