# ✨ 影片 AI 畫質修復 & 消除浮水印工具 (Video AI Enhancer)

<p align="center">
  <img src="https://img.shields.io/badge/Version-v1.0.3-blueviolet?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/AI%20Core-Real--ESRGAN%20(Vulkan)-10b981?style=flat-square" alt="Real-ESRGAN">
  <img src="https://img.shields.io/badge/Video%20Engine-FFmpeg-0078D7?style=flat-square&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License">
</p>

基於 **Real-ESRGAN (NCNN Vulkan)** 與 **FFmpeg** 的一站式輕量級桌面端 AI 工具，支援**影片與照片的 4x 超解析度畫質修復**，以及**互動式塗抹消除浮水印 (Inpainting)**。零門檻、免安裝 PyTorch/CUDA 巨量依賴、全便攜化隨開隨用！

---

## 📢 v1.0.3 最新更新日誌 (Changelog)

- 🛡️ **FFmpeg Delogo 現代相容性修正 (解決 Option 'band' not found)**：
  - 徹底移除新版 FFmpeg 已棄用的 `band` 參數，改用全版本標準通用的濾鏡語法 `delogo=x:y:w:h`，全面相容現代所有 FFmpeg 發行版。
  - 保留 $X \ge 1, Y \ge 1$ 動態邊界防護約束，既不觸發未知選項錯誤，又根絕了先前貼邊引發的 `4294967274 (EINVAL)` 崩潰！
- ⚡ **極速畫布平移引擎 (解決放大後畫面卡死/無法移動)**：
  - 徹底重構平移底層，拖曳移動時移除重複的影像雙線性插值計算，改以硬體級畫布同步位移，達成 **0ms 延遲、極致絲滑流暢**。
- ✋ **雙模式切換與全操作手勢支援**：
  - 新增 **`[✏️ 塗抹]`** 與 **`[✋ 平移]`** 模式切換按鈕，筆電觸控板用戶單指/左鍵即可任意移動視角。
  - 支援 **滑鼠右鍵**、**滑鼠中鍵 (滾輪按下)**、**長按空白鍵 (Space) + 左鍵** 隨時拖曳平移。
  - 新增 **`[⛶ 置中]`** 快捷回正按鈕，並支援鍵盤方向鍵（`←` `↑` `→` `↓`）微調平移視角。
- 🔍 **游標焦點縮放 (Zoom to Cursor)**：
  - 使用滑鼠滾輪縮放時，自動以滑鼠指針所在的位置為焦點進行縮放，放大時畫面不再跑偏。

---

## 🎯 效果對比展示 (Before vs After)

> 左圖為 **AI 修復後**（左上角浮水印完全抹除 + 畫質細節重建），右圖為 **修復前**（帶有 RunningHub AI 水印與壓縮失真）。

<p align="center">
  <img src="assets/comparison.jpg" alt="畫質修復與消除浮水印前後對比" width="95%">
</p>

- **浮水印完全消失**：牆面陰影、背景紋理無痕融合，絕不留死白或方形色塊。
- **4x 超解析度紋理補全**：髮絲根根分明，金屬零件、衣物布料與木桌紋理皆由神經網路重新生成銳利細節。

---

## 🖥️ 軟體介面預覽 (Interface Preview)

<p align="center">
  <img src="assets/ui_preview.png" alt="影片 AI 畫質修復工具介面" width="90%">
</p>

---

## 🌟 核心特色功能

### 1. 🚀 AI 畫質修復 (4x 超解析度)
- **多模型支援**：內建 `realesrgan-x4plus (通用照片/真實影片)`、`realesrgan-x4plus-anime (動漫二次元風格)`、`realesrnet-x4plus (平滑抗鋸齒)`。
- **自由縮放倍率**：支援 `2x` / `4x` 放大倍率。
- **即時影片規格分析**：自動提取原始影格率（FPS）、解析度並實時推算輸出尺寸（自動標註 2K QHD / 4K UHD / 8K）。
- **即時逐幀進度條**：以 0.3 秒為單位監聽已完成影格，進度實時跳動，絕不卡死！
- **秒級強制取消**：深度進程樹終止機制，放大到一半隨時可中斷並立即釋放 GPU 算力。

### 2. 🧽 塗抹消除浮水印 (Inpainting)
- **直覺塗抹畫布**：支援載入影片（自動提取首幀預覽）與圖片，滑鼠左鍵自由塗抹遮罩。
- **🔍 畫面縮放與平移**：支援游標焦點滾輪縮放（最高 800%）與多種平移手勢（抓手模式、右鍵/中鍵/Space+左鍵），邊角細微浮水印輕鬆搞定！
- **可調筆刷與 Undo**：提供 5px~80px 筆刷粗細滑桿，支援一鍵復原 (Undo) 與清空標記。
- **🔗 一鍵聯動 AI 放大**：消除浮水印後，可直接點擊「傳送至 AI 放大修復」，自動切換至 AI 頁面無縫進行 4x 超解析度處理！

### 3. ⚡ 全便攜化與通用硬體加速
- **Vulkan GPU 硬體加速**：支援 NVIDIA、AMD、Intel 所有主流顯卡，運算效率高且無需安裝數十 GB 的 CUDA 與 PyTorch。
- **無損音畫合流**：自動提取原始視訊音軌，AI 重建後無損合併，絕不產生音畫不同步或失真。
- **零黑框執行**：全程後台靜默運算，不會彈出任何惱人的黑色 CMD 命令列視窗。

---

## 🚀 快速啟動

雙擊專案目錄下的：
- **`啟動工具(免黑框).vbs`**（推薦，完全無黑框閃爍）
- 或 **`啟動工具.bat`**

若已打包為獨立發行版，可直接雙擊：
- **`影片AI畫質修復工具.exe`**

---

## 📦 一鍵打包為獨立 EXE 執行檔 (v1.0.3)

本專案提供全自動化 PyInstaller 打包腳本：
1. 直接雙擊根目錄的 **`一鍵製作EXE版本(v1.0.3).bat`**。
2. 腳本會自動檢測並編譯最新的 `src/gui.py` 為帶有圖示、無黑框的獨立 **`影片AI畫質修復工具.exe`**。
3. 自動將 AI 模型、FFmpeg 核心及資源封裝至 `release/影片AI畫質修復工具_v1.0.3/`，並自動生成 `影片AI畫質修復工具_v1.0.3.zip` 綠色免安裝壓縮發行包！

---

## 📥 核心環境一鍵下載

若本機尚未具備 AI 核心或 FFmpeg，軟體支援**零設定全自動下載**：
1. **方式 A**：開啟 UI 後，左下角直接點擊 **「⬇️ 一鍵安裝 AI 引擎」**，程式會在介面內自動下載並解壓（約 20MB Real-ESRGAN + 必要組件）。
2. **方式 B**：在資料夾中直接雙擊：
   ```bash
   scripts\一鍵安裝核心.bat
   ```

---

## 📤 推送到 GitHub

本專案已自帶 `.gitignore`（自動排除大於 100MB 的二進位核心檔案與暫存影片，避免觸發 GitHub 100MB 限制）。  
若要將程式碼更新推送至您的 GitHub 倉庫，直接雙擊執行：
```bash
git_push.bat
```

---

## 📄 開源許可
本專案採用 [MIT License](LICENSE) 開源授權。
