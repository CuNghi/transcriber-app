import os
import subprocess

def download_from_drive(folder_url: str, dest: str):
    os.makedirs(dest, exist_ok=True)
    # Use gdown CLI to pull a Drive folder
    subprocess.run([
        "gdown",
        "--folder", folder_url,
        "-O", dest
    ], check=True)

if __name__ == "__main__":
    # … your existing HuggingFace snapshot_download calls …

    # 3) Pull the Google-Drive models folder
    drive_url = "https://drive.google.com/drive/folders/1mrG1FmPocvAs6c6R2qjizFrHNBw1mukS"
    print(f"→ downloading all models from {drive_url}")
    download_from_drive(drive_url, "backend/models")
