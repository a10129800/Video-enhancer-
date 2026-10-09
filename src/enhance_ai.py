import sys, subprocess, shutil, tempfile
from pathlib import Path
from tkinter import Tk, filedialog

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent if CURRENT_DIR.name in ["src", "scripts"] else CURRENT_DIR
CORE_DIR = ROOT_DIR / "core"
BASE_DIR = ROOT_DIR

def get_ffmpeg():
    local_ffmpeg = CORE_DIR / "ffmpeg.exe" if (CORE_DIR / "ffmpeg.exe").exists() else ROOT_DIR / "ffmpeg.exe"
    local_ffprobe = CORE_DIR / "ffprobe.exe" if (CORE_DIR / "ffprobe.exe").exists() else ROOT_DIR / "ffprobe.exe"
    ffmpeg = str(local_ffmpeg) if local_ffmpeg.exists() else shutil.which("ffmpeg")
    ffprobe = str(local_ffprobe) if local_ffprobe.exists() else shutil.which("ffprobe")
    return ffmpeg, ffprobe

def ensure_core():
    local_exe = CORE_DIR / "realesrgan-ncnn-vulkan.exe" if (CORE_DIR / "realesrgan-ncnn-vulkan.exe").exists() else ROOT_DIR / "realesrgan-ncnn-vulkan.exe"
    if not local_exe.exists():
        try:
            import install_all
            install_all.main()
        except Exception:
            try:
                sys.path.append(str(ROOT_DIR / "scripts"))
                import install_all
                install_all.main()
            except Exception:
                pass
    return str(local_exe)

def enhance_ai(input_path: str, model: str = "realesrgan-x4plus", scale: int = 4):
    ffmpeg, ffprobe = get_ffmpeg()
    if not ffmpeg or not ffprobe:
        print("錯誤: 找不到 ffmpeg。請見下方解決方式。")
        return

    bin_esrgan = ensure_core()
    src = Path(input_path)
    dst = src.with_name(f"{src.stem}_ai_enhanced{src.suffix}")
    fps = subprocess.check_output(
        [ffprobe, "-v", "0", "-of", "csv=p=0", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", str(src)],
        text=True
    ).strip()

    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = Path(tmp) / "raw"
        out_dir = Path(tmp) / "out"
        raw_dir.mkdir(); out_dir.mkdir()

        print("1/3 拆幀中...")
        subprocess.run([ffmpeg, "-i", str(src), "-qscale:v", "2", str(raw_dir / "%08d.png")], check=True)
        print("2/3 AI 放大中 (使用 GPU Vulkan 加速)...")
        models_dir = Path(bin_esrgan).parent / "models"
        m_opt = ["-m", str(models_dir)] if models_dir.exists() else []
        subprocess.run([bin_esrgan, "-i", str(raw_dir), "-o", str(out_dir), "-n", model, "-s", str(scale)] + m_opt, check=True)
        print("3/3 封裝影片與原音軌...")
        subprocess.run([
            ffmpeg, "-y", "-r", fps, "-i", str(out_dir / "%08d.png"), "-i", str(src),
            "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", str(dst)
        ], check=True)

    print(f"全部完成！已儲存至: {dst}")

if __name__ == "__main__":
    file = sys.argv[1] if len(sys.argv) > 1 else ""
    if not file:
        root = Tk(); root.withdraw()
        file = filedialog.askopenfilename(title="選擇要提高畫質的影片", filetypes=[("影片", "*.mp4 *.mkv *.avi *.mov")])
    if file:
        enhance_ai(file)
