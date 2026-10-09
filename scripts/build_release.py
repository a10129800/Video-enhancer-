import os
import sys
import shutil
import subprocess
from pathlib import Path

CURRENT = Path(__file__).resolve().parent
BASE_DIR = CURRENT.parent if CURRENT.name in ["scripts", "src"] else CURRENT
RELEASE_DIR = BASE_DIR / "release"
PACKAGE_NAME = "影片AI畫質修復工具_v1.0.0"
TARGET_DIR = RELEASE_DIR / PACKAGE_NAME

def log(msg):
    print(f"[*] {msg}")

def clean_obsolete():
    for f in ["generate_comparison.py", "enhance.py", "啟動圖形介面.bat", "find_enhanced.py", "make_comparison.py", "download_core.py", "README_windows.md"]:
        p = BASE_DIR / f
        if p.exists():
            try: p.unlink()
            except Exception: pass

def ensure_icon():
    log("檢查並生成應用程式圖示 (Icon)...")
    icon_path = BASE_DIR / "assets" / "app_icon.ico"
    if not icon_path.exists():
        try:
            import create_icon
            create_icon.create_app_icon()
            log("已成功生成 assets/app_icon.ico 與 app_icon.png")
        except Exception as e:
            print(f"[!] 生成圖示失敗: {e}")
    else:
        log("圖示已存在: assets/app_icon.ico")

def create_windows_shortcut(target_path, shortcut_path, icon_path=""):
    """使用 Windows 原生 PowerShell 建立專屬 Icon 捷徑"""
    ps = f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut_path}");$s.TargetPath="{target_path}";'
    if icon_path and Path(icon_path).exists():
        ps += f'$s.IconLocation="{icon_path},0";'
    ps += '$s.Save()'
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)
    except Exception:
        pass

def try_pyinstaller():
    """嘗試使用 PyInstaller 打包成單一 EXE 執行檔"""
    try:
        import PyInstaller
        has_pyinstaller = True
    except ImportError:
        has_pyinstaller = False

    if not has_pyinstaller:
        log("尚未安裝 PyInstaller。如需編譯為獨立 .exe，可執行: pip install pyinstaller")
        return False

    log("檢測到 PyInstaller，正在編譯 影片AI畫質修復工具.exe (帶圖示、免命令提示字元黑框)...")
    icon_path = BASE_DIR / "assets" / "app_icon.ico"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--icon={icon_path}",
        "--name=影片AI畫質修復工具",
        "gui.py"
    ]
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    return res.returncode == 0

def build_release_package():
    clean_obsolete()
    ensure_icon()

    # 清理舊的輸出目錄
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR, ignore_errors=True)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    log(f"正在組裝發行包目錄: {TARGET_DIR}")

    # 1. 複製核心引擎與二進位檔
    bin_files = [
        "ffmpeg.exe", "ffprobe.exe", "realesrgan-ncnn-vulkan.exe",
        "vcomp140.dll", "vcomp140d.dll"
    ]
    for b in bin_files:
        src = BASE_DIR / b
        if src.exists():
            shutil.copy2(src, TARGET_DIR / b)
            log(f"已包含核心: {b}")

    # 2. 複製 AI 模型目錄
    models_dir = BASE_DIR / "models"
    if models_dir.exists():
        shutil.copytree(models_dir, TARGET_DIR / "models", dirs_exist_ok=True)
        log("已包含 AI 模型資料夾: models/")

    # 3. 複製資源檔案 assets
    assets_dir = BASE_DIR / "assets"
    if assets_dir.exists():
        shutil.copytree(assets_dir, TARGET_DIR / "assets", dirs_exist_ok=True)
        log("已包含圖示資源: assets/")

    # 4. 檢查是否有 PyInstaller 編譯好的 exe
    built_exe = BASE_DIR / "dist" / "影片AI畫質修復工具" / "影片AI畫質修復工具.exe"
    exe_packaged = False
    if built_exe.exists():
        log("將 PyInstaller 生成的二進位組件複製進發行包...")
        for item in (BASE_DIR / "dist" / "影片AI畫質修復工具").iterdir():
            dest = TARGET_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        exe_packaged = True

    # 5. 複製 Python 腳本（免安裝環境直接雙擊亦可運行）
    scripts = ["gui.py", "enhance_ai.py", "install_all.py", "create_icon.py"]
    for s in scripts:
        src = BASE_DIR / s
        if src.exists():
            shutil.copy2(src, TARGET_DIR / s)

    # 6. 製作帶有專屬 Icon 的 Windows 啟動捷徑與免黑框啟動器
    icon_target = TARGET_DIR / "assets" / "app_icon.ico"
    
    # 建立無黑框 VBS 入口
    vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\n'
    vbs_content += 'WshShell.Run "pythonw gui.py", 0, False\n'
    vbs_path = TARGET_DIR / "啟動工具(免黑框).vbs"
    vbs_path.write_text(vbs_content, encoding="utf-8")

    # 建立 BAT 入口
    bat_content = '@echo off\nchcp 65001 >nul\ncd /d "%~dp0"\nstart pythonw gui.py\nexit\n'
    bat_path = TARGET_DIR / "啟動工具.bat"
    bat_path.write_text(bat_content, encoding="utf-8")

    # 建立專屬捷徑 (如果打包了 exe 就指向 exe，否則指向 vbs)
    shortcut_path = TARGET_DIR / "影片AI畫質修復工具.lnk"
    if exe_packaged and (TARGET_DIR / "影片AI畫質修復工具.exe").exists():
        target_exec = TARGET_DIR / "影片AI畫質修復工具.exe"
        create_windows_shortcut(target_exec, shortcut_path, icon_target)
    else:
        create_windows_shortcut(vbs_path, shortcut_path, icon_target)
    log("已建立帶有專屬 App Icon 的快速啟動捷徑: 影片AI畫質修復工具.lnk")

    # 7. 建立說明文件
    readme_text = f"""========================================================
  ✨ 影片 AI 畫質修復 & 消除浮水印工具 - Release 發行版
========================================================

【快速啟動】
1. 直接雙擊「影片AI畫質修復工具.lnk」或「啟動工具(免黑框).vbs」。
2. 即可開啟圖形介面，隨開隨用！

【核心組件清單】
- Real-ESRGAN-ncnn-vulkan (AI 超解析度修復核心)
- FFmpeg & FFprobe (影音串流解碼與無失真封裝)
- models/ (內建超解析度 AI 模型)
- OpenCV / Pillow (浮水印塗抹修復演算法)

【注意事項】
- 支援各大顯示卡 (NVIDIA / AMD / Intel GPU)，透過 Vulkan 硬體加速運算。
- 感謝您的使用！
"""
    (TARGET_DIR / "使用說明_README.txt").write_text(readme_text, encoding="utf-8")

    # 8. 自動打包成 ZIP 壓縮檔
    log("正在將發行版壓縮為 ZIP 存檔...")
    zip_output = RELEASE_DIR / PACKAGE_NAME
    shutil.make_archive(str(zip_output), "zip", root_dir=str(RELEASE_DIR), base_dir=PACKAGE_NAME)
    log(f"壓縮完成！發行檔已儲存至: {zip_output}.zip")

    print("\n" + "=" * 56)
    print(f"🎉 Release 發行版打包成功！")
    print(f"📁 資料夾: {TARGET_DIR}")
    print(f"📦 壓縮包: {zip_output}.zip")
    print("=" * 56)

if __name__ == "__main__":
    print("=" * 60)
    print("  ✨ 影片 AI 畫質修復工具 - Release 發行版打包精靈")
    print("=" * 60)
    print()
    print("請選擇打包模式:")
    print("  [1] 快速可攜式發行包 (推薦: 綠色版 + 專屬 Icon 捷徑 + ZIP 壓縮檔)")
    print("  [2] PyInstaller 編譯獨立 EXE 模式 (編譯為無黑框 .exe 後封裝)")
    print("  [3] 僅生成/更新高清 App Icon (assets/app_icon.ico)")
    print()
    
    try:
        user_choice = input("請輸入選項 [1, 2 或 3，預設 1]: ").strip()
    except Exception:
        user_choice = "1"
        
    if user_choice == "3":
        ensure_icon()
        print("[*] Icon 圖示已生成完成！")
    elif user_choice == "2":
        ensure_icon()
        # 檢查或嘗試安裝 PyInstaller
        try:
            import PyInstaller
        except ImportError:
            print("[*] 正在安裝 PyInstaller...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
        try_pyinstaller()
        build_release_package()
        try:
            subprocess.run(["explorer", str(RELEASE_DIR)])
        except Exception:
            pass
    else:
        build_release_package()
        try:
            subprocess.run(["explorer", str(RELEASE_DIR)])
        except Exception:
            pass
