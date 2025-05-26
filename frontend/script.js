// ─── SSE Progress (multi-attempt capable) ───────────────────────────────────
const stageOrder = [
  'normalization',
  'chunking',
  'diarization',
  'transcription',
  'finishing',
  'complete'
];
const iconMap = {
  normalization: 'norm-icon',
  chunking:      'chunk-icon',
  diarization:   'diar-icon',
  transcription: 'trans-icon',
  finishing:     'fin-icon'
};

let evtSource = null;
function startProgressStream() {
  if (evtSource) evtSource.close();
  evtSource = new EventSource('/progress');
  evtSource.onmessage = e => {
    const stage = e.data;
    const idx   = stageOrder.indexOf(stage);
    if (idx < 0) return;
    const pct = ((idx+1)/stageOrder.length)*100;
    document.getElementById('progress-bar').value = pct;
    stageOrder.slice(0,stageOrder.length-1).forEach((s,i) => {
      const el = document.getElementById(iconMap[s]);
      if (!el) return;
      el.textContent = i<idx ? '✅' : (i===idx ? '🔄':'⏳');
    });
    if (stage==='complete') evtSource.close();
  };
}
window.addEventListener('DOMContentLoaded', () => {
  startProgressStream();
});

// ─── DOM References & State ─────────────────────────────────────────────────
const form               = document.getElementById('upload-form');
const audioEl            = document.getElementById('audio');
const speedSelect        = document.getElementById('speed-select');
const playBtn            = document.getElementById('global-play');
const pauseBtn           = document.getElementById('global-pause');
const transcriptEl       = document.getElementById('transcript');

const exportSelect = document.getElementById('export-select');
const exportBtn    = document.getElementById('export-btn');


const enableDiarCheckbox = document.getElementById('enable-diarization');
const hiddenDiarizer     = document.getElementById('hidden-diarizer');
const speakersSel        = document.getElementById('speakers-select');
const speakerSettings    = document.getElementById('speaker-settings');
const guestNamesDiv      = document.getElementById('guest-names');

const resourcesBtns      = document.querySelectorAll('.resources-btn');
const hiddenCoresInput   = document.getElementById('hidden-cores');

let segments     = [];
let isPlayingAll = false;
let playStart    = 0;
let playEnd      = 0;
let onTimeUpdate = null;
let defaultDiarizer = 'none';

// ─── Initialize playback rate ────────────────────────────────────────────────
audioEl.addEventListener('loadedmetadata', () => {
  playBtn.disabled = false;
  playEnd = audioEl.duration;
  audioEl.playbackRate = parseFloat(speedSelect.value);
});
speedSelect.addEventListener('change', () => {
  audioEl.playbackRate = parseFloat(speedSelect.value);
});

// ─── Audio Playback Helpers ─────────────────────────────────────────────────
function removeTimeUpdate() {
  if (!onTimeUpdate) return;
  audioEl.removeEventListener('timeupdate', onTimeUpdate);
  onTimeUpdate = null;
}
function startPlayback() {
  removeTimeUpdate();
  audioEl.currentTime = playStart;
  audioEl.play();
  onTimeUpdate = () => {
    const t = audioEl.currentTime;
    segments.forEach(s => {
      s.el.classList.toggle('playing', t>=s.start && t<s.end);
    });
    if (t>=playEnd) {
      audioEl.pause();
      removeTimeUpdate();
      if (isPlayingAll) {
        playBtn.disabled  = false;
        pauseBtn.disabled = true;
      }
    }
  };
  audioEl.addEventListener('timeupdate', onTimeUpdate);
}
playBtn.addEventListener('click', () => {
  if (!segments.length) return;
  isPlayingAll   = true;
  playStart      = 0;
  playEnd        = audioEl.duration;
  playBtn.disabled  = true;
  pauseBtn.disabled = false;
  startPlayback();
});
pauseBtn.addEventListener('click', () => {
  isPlayingAll = false;
  audioEl.pause();
  removeTimeUpdate();
  playBtn.disabled  = false;
  pauseBtn.disabled = true;
  segments.forEach(s => s.el.classList.remove('playing'));
});
function playSingle(start,end,el) {
  const prevAll = isPlayingAll;
  isPlayingAll  = prevAll;
  playStart     = start;
  playEnd       = prevAll ? audioEl.duration : end;
  playBtn.disabled  = prevAll;
  pauseBtn.disabled = !prevAll;
  startPlayback();
}

// ─── Populate & Wire Up Advanced Controls ───────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  const res  = await fetch('/plugins');
  const opts = await res.json();
  // 1) Diarizer
  defaultDiarizer = opts.diarizers.find(d=>d!=='none')||'none';
  hiddenDiarizer.value = defaultDiarizer;
  enableDiarCheckbox.checked = true;
  // 2) Speakers
  speakersSel.innerHTML = '';
  opts.speakers.forEach(n=>{
    const o = document.createElement('option');
    o.value = o.textContent = n;
    speakersSel.appendChild(o);
  });
  speakersSel.value = 2;
  // 3) Engines
  const [acc,spd] = opts.engines;
  document.getElementById('mode-accuracy').value = acc;
  document.getElementById('mode-speed')   .value = spd||acc;
  // 4) Cores
  const coresList = opts.cores.map(String);
  resourcesBtns.forEach(btn=>{
    btn.addEventListener('click',()=>{
      resourcesBtns.forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      const pct = parseInt(btn.dataset.percent,10);
      const idx = Math.round((coresList.length-1)*pct/100);
      hiddenCoresInput.value = coresList[idx];
    });
  });
  document.querySelector('.resources-btn[data-percent="50"]').click();


  // restore last export choice
  const lastChoice = localStorage.getItem('exportChoice');
  if (lastChoice && exportSelect.querySelector(`option[value="${lastChoice}"]`)) {
    exportSelect.value = lastChoice;
  }
    exportSelect.addEventListener('change', () => {
    localStorage.setItem('exportChoice', exportSelect.value);
  });

  // 5) Diar toggle & guest inputs
  enableDiarCheckbox.addEventListener('change', () => {
    toggleSpeakerUI();
    generateGuestInputs();
  });
  speakersSel.addEventListener('change', generateGuestInputs);

  toggleSpeakerUI();
  generateGuestInputs();
});

function toggleSpeakerUI() {
  const on = enableDiarCheckbox.checked;
  hiddenDiarizer.value = on ? defaultDiarizer : 'none';
  speakerSettings.style.display    = on?'':'none';
  guestNamesDiv.style.display      = on?'':'none';
  document.getElementById('diar-progress')
          .style.display = on?'':'none';
}

function generateGuestInputs() {
  const n = parseInt(speakersSel.value)||1;
  guestNamesDiv.innerHTML = '';
  for (let i=1;i<n;i++){
    const wrapper = document.createElement('div');
    const label   = document.createElement('label');
    label.textContent = `Guest ${String(i).padStart(2,'0')} Name: `;
    const inp     = document.createElement('input');
    inp.type      = 'text';
    inp.name      = `guest_name_${i}`;
    inp.placeholder = `Guest ${String(i).padStart(2,'0')}`;
    label.appendChild(inp);
    wrapper.appendChild(label);
    guestNamesDiv.appendChild(wrapper);
  }
}

// ─── Upload & Render Transcript with Speaker Labels ─────────────────────────
form.addEventListener('submit',async e=>{
  e.preventDefault();
  // reset icons & progress
  ['norm-icon','chunk-icon','diar-icon','trans-icon','fin-icon']
    .forEach(id=>{
      const el = document.getElementById(id);
      if(el) el.textContent = '⏳';
    });
  document.getElementById('progress-bar').value = 0;

  // restart SSE
  startProgressStream();

  // POST
  const res  = await fetch('/upload',{method:'POST',body:new FormData(form)});
  const json = await res.json();

  // audio
  audioEl.src = json.norm_url;
  audioEl.load();

  // clear
  transcriptEl.innerHTML = '';
  segments = [];

  // guest names map
  const totalSpeakers = parseInt(speakersSel.value)||1;
  const guestNames = {};
  for (let i=1;i<totalSpeakers;i++){
    const v = form.elements[`guest_name_${i}`]?.value.trim();
    guestNames[i] = v || `Guest ${String(i).padStart(2,'0')}`;
  }

  // time formatter
  const fmt = t=>{
    const hh = String(Math.floor(t/3600)).padStart(2,'0');
    const mm = String(Math.floor((t%3600)/60)).padStart(2,'0');
    const ss = String(Math.floor(t%60)).padStart(2,'0');
    return `${hh}:${mm}:${ss}`;
  };

  json.segments
    .filter(s=>Array.isArray(s.words)&&s.words.length)
    .forEach(seg=>{
      // build speaker list
      const allLabels = [...new Set(json.segments
        .map(s=>s.speaker)
        .filter(l=>'global'!==l)
      )];
      let idx = seg.speaker==='global'
        ? 0
        : allLabels.indexOf(seg.speaker)+1;

      // choose label
      let label = '';
      if (idx===2){
        label = 'Ilana Razbash';
      } else if (idx>1){
        label = guestNames[idx-2] 
          || `Guest ${String(idx-1).padStart(2,'0')}`;
      }

      const start = seg.words[0].start;
      const end   = seg.words[seg.words.length-1].end;

      const block = document.createElement('div');
      block.classList.add('segment');

      // timestamp
      const ts = document.createElement('span');
      ts.classList.add('timestamp');
      ts.textContent = `[${fmt(start)}] `;
      ts.addEventListener('click',()=>playSingle(start,end,block));
      block.appendChild(ts);

      // speaker label (only if not global)
      if (label){
        const sp = document.createElement('span');
        sp.classList.add('speaker-label');
        sp.innerHTML = `<strong>${label}:</strong> `;
        block.appendChild(sp);
      }

      // text
      const txt = document.createElement('span');
      txt.textContent = seg.text.trim();
      block.appendChild(txt);

      // right-click seek
      block.addEventListener('contextmenu',ev=>{
        ev.preventDefault();
        playSingle(start,end,block);
      });

      transcriptEl.appendChild(block);
      segments.push({start,end,el:block});
    });
});

// ─── Save Script & CSV ──────────────────────────────────────────────────────
exportBtn.addEventListener('click', () => {
  const choice = exportSelect.value;
  const audioFile = form.elements['audio'].files[0]?.name || '';
  const baseName  = audioFile.replace(/\.[^/.]+$/, '') || 'transcript';

  // helper to download a blob
  function download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a   = document.createElement('a');
    a.href    = url;
    a.download= filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // persist last choice
  localStorage.setItem('exportChoice', choice);

  if (choice === 'script') {
    // exactly your existing “Save Script” code:
    let txt = 'Transcription:\n\n';
    segments.forEach(s => {
      const h   = String(Math.floor(s.start/3600)).padStart(2,'0');
      const m   = String(Math.floor((s.start%3600)/60)).padStart(2,'0');
      const sec = String(Math.floor(s.start%60)).padStart(2,'0');
      txt += `[${h}:${m}:${sec}] ${s.el.innerText}\n\n`;
    });
    const blob = new Blob([txt], { type: 'text/plain' });
    download(blob, `${baseName}_script.txt`);
  }
  else if (choice === 'csv-formatted') {
    // your existing “Save CSV (with tags)” code
    const numSpeakers = parseInt(speakersSel.value) || 2;
    const guestList   = [];
    for (let i = 1; i < numSpeakers; i++) {
      const v = form.elements[`guest_name_${i}`]?.value.trim();
      if (v) guestList.push(v);
    }
    const meta = {
      'Title':           form.elements['title'].value,
      'Broadcast Date':  form.elements['broadcast_date'].value,
      'Guest Name':      guestList.join(','),
      'Subtitle':        form.elements['subtitle'].value,
      'Image':           form.elements['image'].value,
      'Transcription':   (() => {
        let html = transcriptEl.innerHTML
          .replace(/<div class="segment">/g, '')
          .replace(/<\/div>/g, '\n')
          .trim();
        return html;
      })(),
      'Tags':            form.elements['tags'].value,
      'Backlinks':       form.elements['backlinks'].value,
      'Image Alt Text':  form.elements['image_alt_text'].value
    };
    const headers = [
      'Title','Broadcast Date','Guest Name','Subtitle',
      'Image','Transcription','Tags','Backlinks','Image Alt Text'
    ];
    const values = headers.map(h => `"${(meta[h]||'').replace(/"/g,'""')}"`);
    const csvText = [ headers.join(','), values.join(',') ].join('\n');
    download(new Blob([csvText], { type:'text/csv' }), `${baseName}_transcription.csv`);
  }
  else if (choice === 'csv-plain') {
    // your existing “Save CSV (plain text)” code
    const numSpeakers = parseInt(speakersSel.value) || 2;
    const guestList   = [];
    for (let i = 1; i < numSpeakers; i++) {
      const v = form.elements[`guest_name_${i}`]?.value.trim();
      if (v) guestList.push(v);
    }
    const meta = {
      'Title':           form.elements['title'].value,
      'Broadcast Date':  form.elements['broadcast_date'].value,
      'Guest Name':      guestList.join(','),
      'Subtitle':        form.elements['subtitle'].value,
      'Image':           form.elements['image'].value,
      'Transcription':   transcriptEl.innerText.trim(),
      'Tags':            form.elements['tags'].value,
      'Backlinks':       form.elements['backlinks'].value,
      'Image Alt Text':  form.elements['image_alt_text'].value
    };
    const headers = [
      'Title','Broadcast Date','Guest Name','Subtitle',
      'Image','Transcription','Tags','Backlinks','Image Alt Text'
    ];
    const values = headers.map(h => `"${(meta[h]||'').replace(/"/g,'""')}"`);
    const csvText = [ headers.join(','), values.join(',') ].join('\n');
    download(new Blob([csvText], { type:'text/csv' }), `${baseName}_plain_transcription.csv`);
  }
});

// ─── Clean shutdown ─────────────────────────────────────────────────────────
window.addEventListener('unload', () => {
  navigator.sendBeacon('/shutdown');
});
