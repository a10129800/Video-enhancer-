import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def run_cmd(cmd, check=True):
    return subprocess.run(cmd, cwd=str(ROOT_DIR), check=check)

def main():
    print("=" * 60)
    print("  🚀 影片 AI 畫質修復工具 - GitHub 一鍵推送精靈")
    print("=" * 60)
    print()

    # 1. 檢查 Git
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        print("[錯誤] 系統未安裝 Git，或未將 Git 加入環境變數！")
        print("請先安裝 Git: https://git-scm.com/")
        input("\n按 Enter 鍵結束...")
        return

    # 2. 自動執行清理
    try:
        import clean
        clean.clean()
    except Exception:
        pass

    # 3. 檢查 git init
    if not (ROOT_DIR / ".git").exists():
        print("[*] 正在初始化本地 Git 倉庫...")
        run_cmd(["git", "init"])
        run_cmd(["git", "branch", "-M", "main"])

    # 4. 檢查 Remote
    res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(ROOT_DIR), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("[*] 尚未綁定 GitHub 遠端倉庫！")
        repo_url = input("請貼上您的 GitHub 倉庫網址 (例如 https://github.com/用戶名/專案名.git): ").strip()
        if not repo_url:
            print("[取消] 未輸入網址，取消推送。")
            return
        run_cmd(["git", "remote", "add", "origin", repo_url])

    # 5. Commit 說明
    default_msg = "feat: 影片 AI 畫質修復與塗抹去浮水印工具 (深度模組化架構)"
    user_msg = input(f"\n請輸入 Commit 說明 (直接按 Enter 使用預設說明): ").strip()
    commit_msg = user_msg if user_msg else default_msg

    print()
    print("[*] 正在暫存變更檔案 (已自動排除大於 100MB 核心與暫存檔)...")
    run_cmd(["git", "add", "."])

    print(f"[*] 正在建立 Commit: {commit_msg}")
    run_cmd(["git", "commit", "-m", commit_msg], check=False)

    print("[*] 正在推送至 GitHub main 分支...")
    push_res = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(ROOT_DIR))
    if push_res.returncode == 0:
        print("\n" + "=" * 60)
        print("🎉 恭喜！專案已成功推送到 GitHub！")
        print("=" * 60)
    else:
        print("\n[!] 若為首次推送且遠端已有 README，可先執行: git pull --rebase origin main")

    input("\n請按 Enter 鍵退出...")

if __name__ == "__main__":
    main()
