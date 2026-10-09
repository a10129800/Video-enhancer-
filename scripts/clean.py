import os
import shutil
from pathlib import Path

CURRENT = Path(__file__).resolve().parent
BASE_DIR = CURRENT.parent if CURRENT.name in ["scripts", "src"] else CURRENT

def clean():
    print("=" * 50)
    print("  🧹 正在進行專案清理與瘦身...")
    print("=" * 50)

    # 1. 要刪除的單一檔案清單
    files_to_delete = [
        "generate_comparison.py",
        "enhance.py",
        "app_icon.ico",            # 根目錄重複圖示 (保留 assets/app_icon.ico)
        "find_enhanced.py",
        "make_comparison.py",
        "download_core.py",
        "README_windows.md",
        "temp_thumb.jpg",
        "temp_preview.jpg",
        "comp_before.jpg",
        "comp_after.jpg",
        "deploy_images.py",
        "organize.py",
        "_mklink.vbs",
    ]

    deleted_count = 0
    for name in files_to_delete:
        p = BASE_DIR / name
        if p.exists():
            try:
                p.unlink()
                print(f"[已刪除檔案] {name}")
                deleted_count += 1
            except Exception as e:
                print(f"[無法刪除] {name}: {e}")

    # 2. 清理模式檔案 (*.spec)
    for p in BASE_DIR.glob("*.spec"):
        try:
            p.unlink()
            print(f"[已刪除規格檔] {p.name}")
            deleted_count += 1
        except Exception:
            pass

    # 3. 清理建置與快取目錄 (build, dist, __pycache__)
    dirs_to_delete = ["build", "dist", "__pycache__"]
    for d in dirs_to_delete:
        dp = BASE_DIR / d
        if dp.exists():
            try:
                shutil.rmtree(dp, ignore_errors=True)
                print(f"[已清除目錄] {d}/")
                deleted_count += 1
            except Exception as e:
                print(f"[無法清除目錄] {d}/: {e}")

    print("=" * 50)
    print(f"✨ 清理完成！共處理 {deleted_count} 個冗餘項目。")
    print("專案目錄已維持在最精簡、清爽狀態！")
    print("=" * 50)

if __name__ == "__main__":
    clean()
