import urllib.request, zipfile, io, shutil
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent if CURRENT_DIR.name in ["src", "scripts"] else CURRENT_DIR
CORE_DIR = ROOT_DIR / "core"
CORE_DIR.mkdir(parents=True, exist_ok=True)
TARGET_DIR = CORE_DIR

ESRGAN_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def download_and_extract(name: str, url: str, extract_filter=None):
    print(f"\n[1/2] 正在下載 {name}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        data = bytearray()
        while chunk := resp.read(1024 * 128):
            data.extend(chunk)
            if total:
                percent = len(data) / total * 100
                print(f"\r下載進度: {percent:.1f}% ({len(data)//1024//1024}MB / {total//1024//1024}MB)", end="", flush=True)

    print(f"\n[2/2] 正在解壓縮 {name} 至 core/...")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if extract_filter:
            extract_filter(z, TARGET_DIR)
        else:
            z.extractall(TARGET_DIR)
    print(f"-> {name} 部署完成！")

def extract_ffmpeg(z: zipfile.ZipFile, dest: Path):
    for member in z.namelist():
        if member.endswith("ffmpeg.exe"):
            with z.open(member) as src, open(dest / "ffmpeg.exe", "wb") as dst:
                shutil.copyfileobj(src, dst)
        elif member.endswith("ffprobe.exe"):
            with z.open(member) as src, open(dest / "ffprobe.exe", "wb") as dst:
                shutil.copyfileobj(src, dst)

def main():
    print("==================================================")
    print("  畫質提高工具 - 全自動核心環境下載器")
    print("==================================================")

    # 1. 檢查/下載 FFmpeg
    has_ff = (CORE_DIR / "ffmpeg.exe").exists() or (ROOT_DIR / "ffmpeg.exe").exists()
    has_probe = (CORE_DIR / "ffprobe.exe").exists() or (ROOT_DIR / "ffprobe.exe").exists()
    if not (has_ff and has_probe):
        download_and_extract("FFmpeg (約 90MB)", FFMPEG_URL, extract_ffmpeg)
    else:
        print("[已存在] FFmpeg 與 FFprobe 核心已就緒。")

    # 2. 檢查/下載 Real-ESRGAN
    has_esrgan = (CORE_DIR / "realesrgan-ncnn-vulkan.exe").exists() or (ROOT_DIR / "realesrgan-ncnn-vulkan.exe").exists()
    if not has_esrgan:
        download_and_extract("Real-ESRGAN AI 核心 (約 20MB)", ESRGAN_URL)
    else:
        print("[已存在] Real-ESRGAN AI 核心已就緒。")

    print("\n==================================================")
    print(" 全部必備組件已安裝齊全！現在可直接運行 enhance_ai.py")
    print("==================================================")

if __name__ == "__main__":
    main()
