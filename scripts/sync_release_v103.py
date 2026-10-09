import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL_DIR = ROOT / "release"
V100_DIR = REL_DIR / "影片AI畫質修復工具_v1.0.0"
V103_DIR = REL_DIR / "影片AI畫質修復工具_v1.0.3"

def sync():
    V103_DIR.mkdir(parents=True, exist_ok=True)
    
    # 複製 v1.0.0 裡面的運行環境
    if V100_DIR.exists():
        for item in V100_DIR.iterdir():
            dest = V103_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
                
    # 覆蓋為最新的 src/gui.py
    src_gui = ROOT / "src" / "gui.py"
    if src_gui.exists():
        shutil.copy2(src_gui, V103_DIR / "gui.py")
        (V103_DIR / "src").mkdir(exist_ok=True)
        shutil.copy2(src_gui, V103_DIR / "src" / "gui.py")
        
    # 複製 core 核心二進位檔
    core_dir = ROOT / "core"
    if core_dir.exists():
        dest_core = V103_DIR / "core"
        dest_core.mkdir(exist_ok=True)
        for item in core_dir.iterdir():
            d = dest_core / item.name
            if item.is_dir():
                shutil.copytree(item, d, dirs_exist_ok=True)
            else:
                shutil.copy2(item, d)
                shutil.copy2(item, V103_DIR / item.name)

    # 複製 assets
    assets_dir = ROOT / "assets"
    if assets_dir.exists():
        shutil.copytree(assets_dir, V103_DIR / "assets", dirs_exist_ok=True)

    print("[*] release/影片AI畫質修復工具_v1.0.3 目錄已同步備妥！")

if __name__ == "__main__":
    sync()
