# backend/chunking.py

import os
import ffmpeg
import wave,re
from config import CHUNKS_FOLDER

def split_segments(diar, audio_path):
    """
    Turn a pyannote Annotation into a list of 4-tuples:
      (chunk_wav_path, speaker_label, absolute_start_sec, absolute_end_sec)

    Gaps *between* diarized segments (and before the first / after the last)
    are emitted as “silence” chunks.
    """
    os.makedirs(CHUNKS_FOLDER, exist_ok=True)

    # 1) figure out total duration
    try:
        info = ffmpeg.probe(audio_path)
        total_dur = float(info['format']['duration'])
    except Exception:
        with wave.open(audio_path, 'rb') as wf:
            total_dur = wf.getnframes() / wf.getframerate()

    # 2) collect all (start, end, speaker)
    turns = []
    for spk in diar.labels():
        for seg in diar.label_timeline(spk):
            turns.append((float(seg.start), float(seg.end), spk))
    turns.sort(key=lambda x: x[0])

    # 3) build a new list inserting silence gaps
    enriched = []
    prev_end = 0.0
    eps = 1e-3
    for start, end, spk in turns:
        if start > prev_end + eps:
            enriched.append((prev_end, start, 'silence'))
        enriched.append((start, end, spk))
        prev_end = end
    # tail silence
    if prev_end < total_dur - eps:
        enriched.append((prev_end, total_dur, 'silence'))

    # 4) merge adjacent segments with same label
    merged = []
    for st, en, spk in enriched:
        if merged and merged[-1][2] == spk and st <= merged[-1][1] + eps:
            # extend
            merged[-1] = (merged[-1][0], max(merged[-1][1], en), spk)
        else:
            merged.append((st, en, spk))

    # 5) dump WAV files
    segments = []
    for idx, (st, en, spk) in enumerate(merged):
        out_name = f"{idx:03d}_{spk}_{st:.3f}-{en:.3f}.wav"
        out_path = os.path.join(CHUNKS_FOLDER, out_name)
        (
            ffmpeg
            .input(audio_path, ss=st, to=en)
            .output(out_path, ar='16k', ac=1, format='wav')
            .overwrite_output()
            .run(quiet=True)
        )
        segments.append((out_path, spk, st, en))

    return segments

def split_silence_segments(
    audio_path: str,
    silence_thresh: str = "-40dB",
    min_silence_len: float = 0.5,
) -> list[tuple[str, str, float, float]]:
    """
    Use ffmpeg's silencedetect filter to find silent ranges, then
    carve out non-silent chunks.
    Returns a list of (chunk_path, 'global', start_sec, end_sec).
    """
    os.makedirs(CHUNKS_FOLDER, exist_ok=True)

    # 1) Run silencedetect, capture stderr
    _, err = (
        ffmpeg
        .input(audio_path)
        .filter("silencedetect", noise=silence_thresh, duration=min_silence_len)
        .output("pipe:", format="null")
        .run(capture_stdout=True, capture_stderr=True)
    )
    log = err.decode()

    # 2) Parse out silence_start / silence_end timestamps
    starts = [float(m.group(1)) for m in re.finditer(r"silence_start: ([0-9\.]+)", log)]
    ends   = [float(m.group(1)) for m in re.finditer(r"silence_end: ([0-9\.]+)",   log)]

    # 3) Figure out total duration
    with wave.open(audio_path, "rb") as wf:
        total_dur = wf.getnframes() / wf.getframerate()

    # 4) Build non-silent segments
    segments = []
    prev_end = 0.0
    for s, e in zip(starts, ends):
        if s - prev_end > 0.1:  # only if there's actually audio
            out_name = f"{len(segments):03d}_global_{prev_end:.3f}-{s:.3f}.wav"
            out_path = os.path.join(CHUNKS_FOLDER, out_name)
            (
                ffmpeg
                .input(audio_path, ss=prev_end, to=s)
                .output(out_path, ar=16000, ac=1, format="wav")
                .overwrite_output()
                .run(quiet=True)
            )
            segments.append((out_path, "global", prev_end, s))
        prev_end = e

    # 5) Last tail
    if total_dur - prev_end > 0.1:
        start = prev_end
        end   = total_dur
        out_name = f"{len(segments):03d}_global_{start:.3f}-{end:.3f}.wav"
        out_path = os.path.join(CHUNKS_FOLDER, out_name)
        (
            ffmpeg
            .input(audio_path, ss=start, to=end)
            .output(out_path, ar=16000, ac=1, format="wav")
            .overwrite_output()
            .run(quiet=True)
        )
        segments.append((out_path, "global", start, end))

    return segments