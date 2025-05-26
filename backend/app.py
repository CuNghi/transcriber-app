# app.py

import warnings
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="speechbrain.pretrained|pyannote|pytorch_lightning"
)

import os
import shutil
import threading
import webbrowser
import time
import torch
import sys

from flask import Flask, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor

from config import (
    UPLOAD_FOLDER, CHUNKS_FOLDER, ALLOWED_EXT, MAX_WORKERS,
    default_diarizer, default_transcriber,
)
from normalization import normalize_audio
from chunking import split_segments, split_silence_segments
from finishing import clean_text
from exporter import export_csv
from plugins.loader import find_plugins, load_plugin

# ─── HANDLE FROZEN / _MEIPASS ────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    os.environ['PATH'] = base_dir + os.pathsep + os.environ.get('PATH', '')
    PROJECT_ROOT = base_dir
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(base_dir)

# ─── SETUP ───────────────────────────────────────────────────────────────────
for d in (UPLOAD_FOLDER, CHUNKS_FOLDER):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, static_folder=None)

BASE_DIR            = os.path.dirname(__file__)
FRONTEND_DIR        = os.path.join(PROJECT_ROOT, 'frontend')
DIARIZERS_FOLDER    = os.path.join(BASE_DIR, 'plugins', 'diarizers')
TRANSCRIBERS_FOLDER = os.path.join(BASE_DIR, 'plugins', 'transcribers')

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🔍 Detected compute device: {device}")

# ─── GLOBAL STATE & CACHES ───────────────────────────────────────────────────
current_step = ''
diarizer_cache = {}
transcriber_cache = {}

# Preload quick whisper for tiny chunks
quick_mod = load_plugin(TRANSCRIBERS_FOLDER, '2_quick_whisper_transcriber')
quick_mod.initialize(device)
transcriber_cache['2_quick_whisper_transcriber'] = quick_mod


def clean_temp_dirs():
    for fld in (UPLOAD_FOLDER, CHUNKS_FOLDER):
        for fn in os.listdir(fld):
            p = os.path.join(fld, fn)
            try:
                if os.path.isfile(p) or os.path.islink(p):
                    os.unlink(p)
                elif os.path.isdir(p):
                    shutil.rmtree(p)
            except Exception:
                pass


# ─── PROGRESS STREAM ─────────────────────────────────────────────────────────
@app.route('/progress')
def progress():
    def generate():
        last = None
        while True:
            if current_step != last:
                yield f"data:{current_step}\n\n"
                last = current_step
                if last == 'complete':
                    break
            time.sleep(0.1)
    return Response(generate(), mimetype='text/event-stream')


@app.route('/shutdown', methods=['POST'])
def shutdown():
    clean_temp_dirs()
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    else:
        os._exit(0)
    return 'Server shutting down.', 200


# ─── STATIC & PLUGINS INFO ───────────────────────────────────────────────────
def allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXT

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route('/plugins')
def plugins():
    return jsonify({
        'diarizers': ['none'] + find_plugins(DIARIZERS_FOLDER),
        'engines':   find_plugins(TRANSCRIBERS_FOLDER),
        'cores':     list(range(1, MAX_WORKERS + 1)),
        'speakers':  list(range(1, 11)),
    })


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────
@app.route('/upload', methods=['POST'])
def upload():
    global current_step

    # 1) Validate & save upload
    f = request.files.get('audio')
    if not f or not allowed(f.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    fn      = secure_filename(f.filename)
    in_path = os.path.join(UPLOAD_FOLDER, fn)
    f.save(in_path)

    # 2) Normalize
    current_step = 'normalization'
    norm_name = normalize_audio(in_path)
    norm_path = os.path.join(UPLOAD_FOLDER, norm_name)
    norm_url  = f"/uploads/{norm_name}"

    # 3) Read advanced options
    sel_diar = request.form.get('diarizer', default_diarizer)
    print("sel_diar =", sel_diar)
    sel_eng  = request.form.get('engine',  default_transcriber)
    workers  = int(request.form.get('cores',  MAX_WORKERS))
    n_spk    = int(request.form.get('num_speakers', 2))

    # 4) Diarize full file (if requested)
    if sel_diar != 'none':
        current_step = 'diarization'
        diar_mod = load_plugin(DIARIZERS_FOLDER, sel_diar)
        full_annotation = diar_mod.diarize(norm_path, n_spk)
    else:
        full_annotation = None

     # 5) Now split and label:
    current_step = 'chunking'
    if full_annotation:
        # split on speaker boundaries
        segs = split_segments(full_annotation, norm_path)
    else:
        # silence-only split
        segs = [
          (f, 'global', st, en)
          for f,_,st,en in split_silence_segments(norm_path)
        ]
    
    # helper: pick the speaker covering the longest overlap in a chunk
    def get_dominant_speaker(annotation, abs_start, abs_end):
        durations = {}
        try:
            for turn, _, spk in annotation.itertracks(yield_label=True):
                st, en = turn.start, turn.end
                ov = max(0, min(en, abs_end) - max(st, abs_start))
                durations[spk] = durations.get(spk, 0) + ov
        except Exception:
            for st, en, spk in annotation:
                ov = max(0, min(en, abs_end) - max(st, abs_start))
                durations[spk] = durations.get(spk, 0) + ov
        return max(durations, key=durations.get) if durations else 'global'


    # 7) Transcription
    current_step = 'transcription'
    if sel_eng not in transcriber_cache:
        mod = load_plugin(TRANSCRIBERS_FOLDER, sel_eng)
        mod.initialize(device)
        transcriber_cache[sel_eng] = mod
    trans_mod = transcriber_cache[sel_eng]

    def process_segment(chunk_file, speaker, abs_start, abs_end):
        duration = abs_end - abs_start
        if speaker == 'silence':
            return {'speaker':'silence','start':abs_start,'end':abs_end,'words':[],'text':''}

        engine = quick_mod if duration < 0.5 else trans_mod
        rec = engine.transcribe(chunk_file)
        for w in rec['words']:
            w['start'] += abs_start
            w['end']   += abs_start
        return {
            'speaker': speaker,
            'start':   abs_start,
            'end':     abs_end,
            'words':   rec['words'],
            'text':    rec['text']
        }

    # 8) Parallelize transcription
    num_workers = min(workers, len(segs) or 1)
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_segment, *args) for args in segs]
        results = [f.result() for f in futures]

    # 9) Grammar finishing
    current_step = 'finishing'
    for r in results:
        r['text'] = clean_text(r['text'])

    # 10) Metadata & export
    guest_names = [
        request.form.get(f'guest_name_{i}') or f"Guest{str(i).zfill(2)}"
        for i in range(1, n_spk)
    ]
    meta = {
        'Title':                          request.form.get('title',''),
        'Broadcast Date':                 request.form.get('broadcast_date',''),
        'Guest Name':                     ','.join(guest_names),
        'Subtitle':                       request.form.get('subtitle',''),
        'Image':                          request.form.get('image',''),
        'Broadcast Recording Audio File': in_path,
        'Tags':                           request.form.get('tags',''),
        'Backlinks':                      request.form.get('backlinks',''),
        'Image Alt Text':                 request.form.get('image_alt_text',''),
    }

    csv_name    = export_csv(meta, results)
    current_step = 'complete'
    return jsonify({
        'csv_url':  f"/download/{csv_name}",
        'segments': results,
        'norm_url': norm_url
    })


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    # auto-open browser once
    threading.Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=True, use_reloader=False)
