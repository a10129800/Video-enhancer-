# 📝 開發日誌與技術踩坑備忘錄 (Development Log & Knowledge Base)

記錄日期：2026-10-09  
專案版本：v1.0.3  
核心模組：`src/gui.py`, `scripts/build_release.py`, `一鍵製作EXE版本(v1.0.3).bat`

---

## 📌 今日重點任務總結 (Summary)

1. **浮水印消除 (Inpainting) 兩階段致命錯誤排查與徹底解決**。
2. **大尺寸縮放畫布平移引擎重構（解決卡死與移動不良問題）**。
3. **完成 v1.0.3 獨立 EXE 發行版全自動打包與 Windows 批次檔字節相容性修復**。

---

## 🔍 今日關鍵技術踩坑與解決方案 (Technical Insights)

### 坑 1：FFmpeg Delogo 貼邊崩潰（代碼 `4294967274` / `EINVAL -22`）
- **現象**：用戶在畫面最頂部塗抹浮水印時，執行失敗並拋出 `exit status 4294967274`。
- **深層根因**：
  - FFmpeg `delogo` 濾鏡核心原理是利用周圍鄰近像素進行平滑插值（Interpolation）。
  - 若浮水印坐標貼近頂部或邊緣（$X=0$ 或 $Y=0$），FFmpeg 內部檢測到邊緣無取樣空間，判定為非法參數並拋出 `AVERROR(EINVAL) = -22`。在 Windows 32 位元無符號整數中即為 $2^{32} - 22 = 4294967274$。
- **解決方案**：
  - 加入物理尺寸等比映射機制，並加上邊界防護約束：
    ```python
    x = max(1, min(media_w - 3, scaled_x1))
    y = max(1, min(media_h - 3, scaled_y1))
    x2 = max(x + 2, min(media_w - 1, scaled_x2))
    y2 = max(y + 2, min(media_h - 1, scaled_y2))
    w, h = x2 - x, y2 - y
    ```
  - 強制確保周圍至少留有 1px 邊界採樣空間，杜絕非法參數崩潰。

---

### 坑 2：新版 FFmpeg 報錯 `Option 'band' to filter 'delogo': Option not found`
- **現象**：加入 `:band=1` 參數後，新版 FFmpeg 報錯拒絕開啟輸出檔。
- **深層根因**：
  - 現代新版 FFmpeg（5.x / 6.x / 7.x）已正式重構/廢棄了 `delogo` 濾鏡的 `band` 選項，僅保留標準的 `x`, `y`, `w`, `h`。
- **解決方案**：
  - 濾鏡參數簡化為現代標準語法：`delogo=x={x}:y={y}:w={w}:h={h}`。
  - 依賴 Python 端先行的物理邊界計算約束，使新舊版本皆能 100% 完美相容。

---

### 坑 3：畫布放大後畫面無法移動 / 拖曳嚴重卡死 (GUI Freeze)
- **現象**：放大（如 300%~500%）後，右鍵拖曳無反應或極度卡頓，視角無法移動。
- **深層根因**：
  - 先前每次滑鼠移動 1px，主執行緒都在同步對幾百萬像素的影像重複執行高耗時的 PIL 雙線性縮放（`resize`），事件隊列嚴重阻塞導致卡死。
  - 且僅綁定滑鼠右鍵，筆記型電腦觸控板用戶極難操作。
- **解決方案**：
  - **平移與縮放徹底解耦**：平移時不再重算 resize，直接呼叫 `canvas.move("all", dx, dy)`，延遲降至 0ms。
  - **全手勢支援**：
    - 工具列提供 `[✏️ 塗抹]` 與 `[✋ 平移]` 模式切換。
    - 同時支援：滑鼠右鍵、滑鼠中鍵（滾輪按下）、長按空白鍵（Space）+ 左鍵隨時平移、鍵盤方向鍵微調。
  - **游標焦點縮放**：滑鼠滾輪以指標所在坐標為焦點進行縮放（Zoom to cursor），畫面不跑偏。
  - 新增 `[⛶ 置中]` 快捷按鈕。

---

### 坑 4：Windows 批次檔執行時字節錯位（`'thon' is not recognized`）
- **現象**：雙擊 `.bat` 時跳出 `'為您編譯' is not recognized` 以及 `'thon' is not recognized`。
- **深層根因**：
  - Windows 繁體中文環境 CMD 預設代碼頁為 950（Big5）。
  - 若 `.bat` 檔以 UTF-8 儲存且包含中文及多字節 Emoji（如 `✨`, `🎉`），CMD 解譯時字節指針發生錯位，吞掉了下一行 `python` 的 `py` 前綴，導致命令變成 `thon`。
- **解決方案**：
  - **核心準則**：所有 Windows `.bat` 批次檔必須保持純 ASCII / 英文代碼，禁止含有多字節中文或 Emoji。
  - 所有友善的中文提示、進度條與排錯輸出，一律由 Python 腳本端透過 Unicode 渲染輸出。

---

## 📦 發行版本交付狀態

- [x] **原始碼**：`src/gui.py` 已更新至 v1.0.3。
- [x] **說明文件**：`README.md` 包含完整更新日誌。
- [x] **發行包目錄**：`release/影片AI畫質修復工具_v1.0.3/`
  - 內含獨立執行檔：`影片AI畫質修復工具.exe`
  - 內含 AI 引擎：`realesrgan-ncnn-vulkan.exe`、`ffmpeg.exe`、`ffprobe.exe`
  - 內含 AI 模型：`models/`
- [x] **發行壓縮檔**：`release/影片AI畫質修復工具_v1.0.3.zip`（綠色免安裝便攜版）
- [x] **自動打包腳本**：根目錄 `一鍵製作EXE版本(v1.0.3).bat`
