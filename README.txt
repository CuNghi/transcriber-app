**TranscriberApp** is a standalone desktop application for audio transcription with diarization and multiple engine support. It bundles Python, your AI models, and FFmpeg into self‐contained executables on Windows or a `.app` on macOS.

---

## 🚀 Features

- **Diarization** via PyAnnote models  
- **Transcription** via Faster Whisper (or alternative engines)  
- **Plugin architecture**: drop new diarizers or transcribers into `backend/plugins/`  
- **Offline-first**: all models are fetched at build time and bundled in the app  
- **Cross-platform**: PyInstaller builds for both macOS and Windows  

---

## 🔧 Prerequisites

- **macOS build**: a Mac with Homebrew  
- **Windows build**: a PC with Python installed  
- **Model access**:  
  - **Public** models require no token  
  - **Private** Hugging Face repos require an env var:  
    ```bash
    export HF_TOKEN="hf_your_token_here"
    ```

---

## 📥 Getting Started

1. **Clone or upload** this repo  
   (_Do not_ include `backend/models/`; models are fetched at build time.)

2. **Install dependencies** (in a virtual env):

   ```bash
   python -m venv venv
   source venv/bin/activate     # or .\venv\Scripts\Activate.ps1 on Windows
   pip install -r requirements.txt
⚙️ Build on macOS
bash
Copy
Edit
# 1) Make sure HF_TOKEN is set if you need private models
# 2) Install Homebrew ffmpeg if missing (the script auto-installs it)

# 3) Make the script executable
chmod +x build-macos.sh

# 4) Run the build
./build-macos.sh

# 5) After completion:
#    • Open the app:
open dist/TranscriberApp.app
#    • Or unzip the artifact:
unzip TranscriberApp-mac.zip && open TranscriberApp.app
🪟 Build on Windows
powershell
Copy
Edit
# 1) Activate your venv
.\venv\Scripts\Activate.ps1

# 2) Install PyInstaller (and gdown if using Drive-hosted models)
pip install pyinstaller gdown

# 3) Fetch models
python backend/download_models.py

# 4) Build the EXE
pyinstaller --windowed --name TranscriberApp backend/app.py

# 5) Run:
dist\TranscriberApp\TranscriberApp.exe
⚙️ Automated CI Builds
macOS: tag a release (git tag v1.0-mac && git push --tags)

Windows: add a similar GitHub Actions workflow on windows-latest

📁 Project Structure
pgsql
Copy
Edit
├── .github/                       
│   └── workflows/
│       └── build-macos.yml       # MacOS build pipeline
├── backend/                       
│   ├── app.py                    
│   ├── chunking.py               
│   ├── config.py                 
│   ├── exporter.py               
│   ├── finishing.py              
│   ├── normalization.py          
│   ├── download_models.py        # pulls HF & Drive models
│   ├── convert_whisper_models.py 
│   └── plugins/                  
│       ├── diarizers/            
│       └── transcribers/         
├── frontend/                      
│   ├── index.html                
│   ├── script.js                 
│   └── style.css                 
├── TranscriberApp-macos.spec     # PyInstaller spec for macOS
├── build-macos.sh                # macOS build wrapper
├── requirements.txt              # Python dependencies
├── README.md                     
└── .gitignore                    
📦 Dependencies
text
Copy
Edit
# Core AI frameworks
speechbrain>=0.5.12
pyannote-audio>=2.3.0
ctranslate2>=2.20.0
onnxruntime>=1.15.0
lightning-fabric>=0.10.0
faster-whisper>=0.0.8

# Packaging & downloads
pyinstaller>=5.11.0
gdown>=4.6.5
huggingface-hub>=0.16.4
requests>=2.31.0
wget>=3.2
⚖️ License
This project is released under Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0): free to use, modify, and share for non-commercial purposes only. See LICENSE for full text.