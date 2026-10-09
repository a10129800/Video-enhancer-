import os, sys, shutil, subprocess, tempfile, threading, urllib.request, zipfile, io, time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent if CURRENT_DIR.name in ["src", "scripts"] else CURRENT_DIR
CORE_DIR = ROOT_DIR / "core"
ASSETS_DIR = ROOT_DIR / "assets"
BASE_DIR = ROOT_DIR

ESRGAN_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def get_binaries():
    local_ff = CORE_DIR / "ffmpeg.exe" if (CORE_DIR / "ffmpeg.exe").exists() else ROOT_DIR / "ffmpeg.exe"
    local_probe = CORE_DIR / "ffprobe.exe" if (CORE_DIR / "ffprobe.exe").exists() else ROOT_DIR / "ffprobe.exe"
    local_esrgan = CORE_DIR / "realesrgan-ncnn-vulkan.exe" if (CORE_DIR / "realesrgan-ncnn-vulkan.exe").exists() else ROOT_DIR / "realesrgan-ncnn-vulkan.exe"
    
    ffmpeg = str(local_ff) if local_ff.exists() else shutil.which("ffmpeg")
    ffprobe = str(local_probe) if local_probe.exists() else shutil.which("ffprobe")
    esrgan = str(local_esrgan) if local_esrgan.exists() else shutil.which("realesrgan-ncnn-vulkan")
    return ffmpeg, ffprobe, esrgan

def get_media_details(ffprobe_path, media_path):
    try:
        cmd = [
            ffprobe_path, "-v", "0", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-show_entries", "format=size",
            "-of", "default=noprint_wrappers=1", str(media_path)
        ]
        out = subprocess.check_output(cmd, text=True, creationflags=CREATE_NO_WINDOW)
        props = {}
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
        w = int(props.get("width", 0))
        h = int(props.get("height", 0))
        fps_raw = props.get("r_frame_rate", "30/1")
        if "/" in fps_raw:
            n, d = fps_raw.split("/")
            fps = round(float(n) / max(1, float(d)), 1)
        else:
            fps = float(fps_raw)
        size_bytes = int(props.get("size", 0)) if props.get("size") else Path(media_path).stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)
        return w, h, fps, size_mb
    except Exception:
        return 0, 0, 0.0, 0.0

class VideoAiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("影片 AI 畫質修復 & 消除浮水印工具")
        self.geometry("820x720")
        self.minsize(740, 620)
        self.configure(bg="#f4f5f7")

        # 設定視窗圖示 (Icon)
        icon_path = BASE_DIR / "assets" / "app_icon.ico"
        if not icon_path.exists():
            try:
                import create_icon
                create_icon.create_app_icon()
            except Exception:
                pass
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except Exception:
                pass

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TNotebook", background="#f4f5f7", borderwidth=0)
        self.style.configure("TNotebook.Tab", font=("Microsoft JhengHei UI", 10), padding=[16, 6])

        self.is_processing = False
        self.cancel_requested = False
        self.current_process = None
        self.is_installing = False
        self.last_output_dir = BASE_DIR

        # 塗抹編輯器與縮放平移狀態
        self.inpaint_file = None
        self.orig_w = 0
        self.orig_h = 0
        self.display_image = None
        self.display_photo = None
        
        self.base_ratio = 1.0
        self.user_zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.brush_size = tk.IntVar(value=25)
        self.undo_stack = []
        self.current_stroke = []
        self.mask_boxes = []
        self.last_clean_result = None

        # Tab 1 預覽圖快顯
        self.enh_thumb_photo = None

        self.model_map = {
            "realesrgan-x4plus (通用照片/真實影片)": "realesrgan-x4plus",
            "realesrgan-x4plus-anime (動漫/二次元風格)": "realesrgan-x4plus-anime",
            "realesrnet-x4plus (平滑抗鋸齒)": "realesrnet-x4plus"
        }

        self.build_ui()
        self.update_engine_status()

    def build_ui(self):
        main_pad = 12

        # 頂部標題區
        top_frame = tk.Frame(self, bg="#f4f5f7")
        top_frame.pack(fill="x", padx=main_pad, pady=(6, 2))

        lbl_title = tk.Label(top_frame, text="✨ 影片 AI 畫質修復 & 消除浮水印工具", font=("Microsoft JhengHei UI", 14, "bold"), bg="#f4f5f7", fg="#1e293b")
        lbl_title.pack(anchor="w")

        self.lbl_status_engine = tk.Label(top_frame, text="檢查中...", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7", fg="#16a34a")
        self.lbl_status_engine.pack(anchor="w", pady=(1, 2))

        # 雙分頁標籤 (Notebook)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=main_pad, pady=(2, 4))

        # 分頁 1: 🚀 AI 畫質修復
        self.tab_enhance = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.tab_enhance, text=" 🚀 AI 畫質修復 (4x 超解析度) ")

        # 分頁 2: 🧽 塗抹消除浮水印
        self.tab_inpaint = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.tab_inpaint, text=" 🧽 塗抹消除浮水印 (Inpainting) ")

        self.build_enhance_tab()
        self.build_inpaint_tab()

        # 進度條與狀態文字
        prog_frame = tk.Frame(self, bg="#f4f5f7")
        prog_frame.pack(fill="x", padx=main_pad, pady=(2, 2))

        lbl_head = tk.Frame(prog_frame, bg="#f4f5f7")
        lbl_head.pack(fill="x")
        self.lbl_info = tk.Label(lbl_head, text="請選擇要修復的檔案...", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7", fg="#334155")
        self.lbl_info.pack(side="left")
        self.lbl_pct = tk.Label(lbl_head, text="", font=("Microsoft JhengHei UI", 9, "bold"), bg="#f4f5f7", fg="#1d4ed8")
        self.lbl_pct.pack(side="right")

        self.progressbar = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.progressbar.pack(fill="x", pady=(2, 2))

        # 處理過程日誌框
        box_log = tk.LabelFrame(self, text=" 處理過程日誌 ", font=("Microsoft JhengHei UI", 9, "bold"), bg="#f4f5f7", padx=8, pady=4)
        box_log.pack(fill="x", padx=main_pad, pady=2)

        log_container = tk.Frame(box_log, bg="#ffffff")
        log_container.pack(fill="x")

        scroll_log = tk.Scrollbar(log_container, orient="vertical")
        scroll_log.pack(side="right", fill="y")

        self.txt_log = tk.Text(
            log_container,
            height=3,
            yscrollcommand=scroll_log.set,
            font=("Microsoft JhengHei UI", 9),
            bg="#ffffff",
            fg="#1e293b",
            insertbackground="#0f172a",
            relief="solid",
            bd=1,
            wrap="word",
            state="disabled"
        )
        self.txt_log.pack(side="left", fill="both", expand=True)
        scroll_log.config(command=self.txt_log.yview)

        # 底部狀態列
        bottom_frame = tk.Frame(self, bg="#f4f5f7")
        bottom_frame.pack(fill="x", padx=main_pad, pady=(2, 6))

        self.btn_install = tk.Button(bottom_frame, text="☑ AI 引擎已安裝", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", fg="#334155", relief="groove", padx=8, pady=2, command=self.start_install_engine)
        self.btn_install.pack(side="left")

    # ==================== 分頁 1 構建 (填補空白區域) ====================
    def build_enhance_tab(self):
        # 1. 待修復清單
        box_list = tk.LabelFrame(self.tab_enhance, text=" 待修復清單 ", font=("Microsoft JhengHei UI", 9, "bold"), bg="#f4f5f7", padx=8, pady=4)
        box_list.pack(fill="x", pady=2)

        btn_row = tk.Frame(box_list, bg="#f4f5f7")
        btn_row.pack(fill="x", pady=(2, 4))

        tk.Button(btn_row, text="➕ 選擇檔案", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", relief="groove", padx=6, pady=2, command=self.add_files_enh).pack(side="left", padx=(0, 4))
        tk.Button(btn_row, text="🗑️ 清空", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", relief="groove", padx=6, pady=2, command=self.clear_files_enh).pack(side="left", padx=(0, 4))
        tk.Button(btn_row, text="📁 開啟資料夾", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", relief="groove", padx=6, pady=2, command=self.open_output_dir).pack(side="left", padx=(0, 10))

        self.btn_cancel_enh = tk.Button(btn_row, text="🛑 取消修復", font=("Microsoft JhengHei UI", 9, "bold"), bg="#fee2e2", fg="#991b1b", relief="groove", padx=10, pady=2, state="disabled", cursor="hand2", command=self.cancel_process)
        self.btn_cancel_enh.pack(side="right")

        self.btn_start_enh = tk.Button(btn_row, text="🚀 開始 AI 畫質修復", font=("Microsoft JhengHei UI", 9, "bold"), bg="#1d4ed8", fg="#ffffff", activebackground="#1e40af", relief="flat", padx=14, pady=2, cursor="hand2", command=self.start_enhance_process)
        self.btn_start_enh.pack(side="right", padx=(0, 6))

        list_container = tk.Frame(box_list, bg="#ffffff")
        list_container.pack(fill="x")
        scroll_y = tk.Scrollbar(list_container, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        self.listbox_enh = tk.Listbox(list_container, height=4, selectmode="extended", yscrollcommand=scroll_y.set, font=("Microsoft JhengHei UI", 9), bg="#ffffff", fg="#0f172a", selectbackground="#0284c7", selectforeground="#ffffff", relief="solid", bd=1)
        self.listbox_enh.pack(side="left", fill="both", expand=True)
        self.listbox_enh.bind("<<ListboxSelect>>", self.on_select_enh_item)
        scroll_y.config(command=self.listbox_enh.yview)

        # 2. 參數區
        box_params = tk.LabelFrame(self.tab_enhance, text=" 修復參數設定 ", font=("Microsoft JhengHei UI", 9, "bold"), bg="#f4f5f7", padx=8, pady=4)
        box_params.pack(fill="x", pady=2)

        p_row = tk.Frame(box_params, bg="#f4f5f7")
        p_row.pack(fill="x", pady=2)
        tk.Label(p_row, text="AI 模型：", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7").pack(side="left")
        self.var_model = tk.StringVar(value="realesrgan-x4plus (通用照片/真實影片)")
        cb_m = ttk.Combobox(p_row, textvariable=self.var_model, values=list(self.model_map.keys()), state="readonly", width=34)
        cb_m.pack(side="left", padx=(0, 16))

        tk.Label(p_row, text="放大倍率：", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7").pack(side="left")
        self.var_scale = tk.StringVar(value="4")
        self.cb_scale_enh = ttk.Combobox(p_row, textvariable=self.var_scale, values=["2", "4"], state="readonly", width=5)
        self.cb_scale_enh.pack(side="left")
        self.cb_scale_enh.bind("<<ComboboxSelected>>", lambda e: self.update_preview_specs())

        # 3. 🌟 原空白區域改建：影片規格與預估增強預覽面板 🌟
        self.box_info = tk.LabelFrame(self.tab_enhance, text=" 檔案規格與 AI 預估分析 ", font=("Microsoft JhengHei UI", 9, "bold"), bg="#f4f5f7", padx=10, pady=6)
        self.box_info.pack(fill="both", expand=True, pady=4)

        info_container = tk.Frame(self.box_info, bg="#f4f5f7")
        info_container.pack(fill="both", expand=True)

        # 左側：縮圖預覽卡片
        thumb_frame = tk.Frame(info_container, bg="#1e2638", width=180, height=130, relief="solid", bd=1)
        thumb_frame.pack(side="left", padx=(0, 16), fill="both")
        thumb_frame.pack_propagate(False)

        self.lbl_enh_thumb = tk.Label(thumb_frame, text="無預覽", bg="#1e2638", fg="#94a3b8", font=("Microsoft JhengHei UI", 10))
        self.lbl_enh_thumb.pack(fill="both", expand=True)

        # 右側：精緻規格比較卡片
        specs_frame = tk.Frame(info_container, bg="#f4f5f7")
        specs_frame.pack(side="left", fill="both", expand=True)

        self.lbl_spec_file = tk.Label(specs_frame, text="請在上方清單中點選檔案以查看規格分析", font=("Microsoft JhengHei UI", 10, "bold"), bg="#f4f5f7", fg="#1e293b", anchor="w")
        self.lbl_spec_file.pack(fill="x", pady=(2, 4))

        self.lbl_spec_res = tk.Label(specs_frame, text="• 原始尺寸：--- ➔ 預計輸出尺寸：---", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7", fg="#475569", anchor="w")
        self.lbl_spec_res.pack(fill="x", pady=2)

        self.lbl_spec_fps = tk.Label(specs_frame, text="• 影格速率 (FPS)：--- | 檔案大小：---", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7", fg="#475569", anchor="w")
        self.lbl_spec_fps.pack(fill="x", pady=2)

        self.lbl_spec_gpu = tk.Label(specs_frame, text="• 加速核心：Vulkan GPU (NCNN 硬體加速引擎)", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7", fg="#16a34a", anchor="w")
        self.lbl_spec_gpu.pack(fill="x", pady=2)

        self.lbl_spec_audio = tk.Label(specs_frame, text="• 聲道處理：自動提取原音頻並在 AI 重建後無損合流", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7", fg="#0284c7", anchor="w")
        self.lbl_spec_audio.pack(fill="x", pady=2)

    def on_select_enh_item(self, event=None):
        sel = self.listbox_enh.curselection()
        if not sel: return
        item_path = self.listbox_enh.get(sel[0])
        self.analyze_enh_file(item_path)

    def update_preview_specs(self):
        sel = self.listbox_enh.curselection()
        if sel:
            item_path = self.listbox_enh.get(sel[0])
            self.analyze_enh_file(item_path)

    def analyze_enh_file(self, filepath):
        ffmpeg, ffprobe, _ = get_binaries()
        p = Path(filepath)
        if not p.exists() or not ffprobe: return

        w, h, fps, mb = get_media_details(ffprobe, p)
        scale = int(self.var_scale.get() or "4")
        out_w = w * scale
        out_h = h * scale

        # 計算畫質稱號 (HD, 2K, 4K, 8K)
        tag = ""
        if out_w >= 7680 or out_h >= 4320: tag = " (8K Ultra HD)"
        elif out_w >= 3840 or out_h >= 2160: tag = " (4K UHD)"
        elif out_w >= 2560 or out_h >= 1440: tag = " (2K QHD)"
        elif out_w >= 1920 or out_h >= 1080: tag = " (1080p FHD)"

        self.lbl_spec_file.config(text=f"📁 檔案：{p.name}")
        self.lbl_spec_res.config(text=f"• 尺寸演化：{w} × {h}  ➔  {out_w} × {out_h}{tag}")
        self.lbl_spec_fps.config(text=f"• 影格率：{fps} FPS | 大小：{mb} MB")

        # 生成預覽圖縮圖
        img_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        preview_p = p
        if p.suffix.lower() not in img_exts and ffmpeg:
            tmp_t = BASE_DIR / "temp_thumb.jpg"
            cmd = [ffmpeg, "-y", "-ss", "00:00:01", "-i", str(p), "-vframes", "1", "-q:v", "2", str(tmp_t)]
            subprocess.run(cmd, creationflags=CREATE_NO_WINDOW)
            if tmp_t.exists(): preview_p = tmp_t

        if HAS_PIL and Path(preview_p).exists():
            try:
                im = Image.open(preview_p).convert("RGB")
                im.thumbnail((176, 126), Image.Resampling.BILINEAR)
                self.enh_thumb_photo = ImageTk.PhotoImage(im)
                self.lbl_enh_thumb.config(image=self.enh_thumb_photo, text="")
            except Exception:
                self.lbl_enh_thumb.config(image="", text="預覽生成失敗")

    # ==================== 分頁 2 構建 (塗抹消除浮水印) ====================
    def build_inpaint_tab(self):
        tool_box = tk.LabelFrame(self.tab_inpaint, text=" 塗抹工具列 ", font=("Microsoft JhengHei UI", 9, "bold"), bg="#f4f5f7", padx=8, pady=4)
        tool_box.pack(fill="x", pady=2)

        row1 = tk.Frame(tool_box, bg="#f4f5f7")
        row1.pack(fill="x", pady=2)

        tk.Button(row1, text="📁 開啟檔案", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", relief="groove", padx=8, pady=2, command=self.open_inpaint_file).pack(side="left", padx=(0, 8))

        tk.Label(row1, text="筆刷粗細：", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7").pack(side="left")
        scale_brush = tk.Scale(row1, from_=5, to=80, orient="horizontal", variable=self.brush_size, showvalue=0, bg="#f4f5f7", length=80, command=self.update_brush_label)
        scale_brush.pack(side="left", padx=(2, 4))
        self.lbl_brush_val = tk.Label(row1, text="25px", font=("Consolas", 9, "bold"), bg="#f4f5f7", width=4)
        self.lbl_brush_val.pack(side="left", padx=(0, 8))

        tk.Label(row1, text="縮放：", font=("Microsoft JhengHei UI", 9), bg="#f4f5f7").pack(side="left")
        tk.Button(row1, text="➕ 放大", font=("Microsoft JhengHei UI", 8), bg="#e2e8f0", relief="groove", padx=4, pady=1, command=self.zoom_in).pack(side="left", padx=1)
        tk.Button(row1, text="➖ 縮小", font=("Microsoft JhengHei UI", 8), bg="#e2e8f0", relief="groove", padx=4, pady=1, command=self.zoom_out).pack(side="left", padx=1)
        tk.Button(row1, text="⟲ 重置", font=("Microsoft JhengHei UI", 8), bg="#e2e8f0", relief="groove", padx=4, pady=1, command=self.zoom_reset).pack(side="left", padx=1)
        self.lbl_zoom = tk.Label(row1, text="100%", font=("Consolas", 8, "bold"), bg="#f4f5f7", fg="#1d4ed8", width=5)
        self.lbl_zoom.pack(side="left", padx=(0, 8))

        tk.Button(row1, text="↩ 復原", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", relief="groove", padx=6, pady=2, command=self.undo_stroke).pack(side="left", padx=(0, 4))
        tk.Button(row1, text="🗑️ 清除標記", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", relief="groove", padx=6, pady=2, command=self.clear_mask).pack(side="left")

        row2 = tk.Frame(tool_box, bg="#f4f5f7")
        row2.pack(fill="x", pady=(4, 2))

        self.btn_run_inpaint = tk.Button(row2, text="✨ 立即消除浮水印", font=("Microsoft JhengHei UI", 9, "bold"), bg="#0284c7", fg="#ffffff", activebackground="#0369a1", relief="flat", padx=12, pady=3, cursor="hand2", command=self.start_inpaint_process)
        self.btn_run_inpaint.pack(side="left", padx=(0, 6))

        self.btn_save_inpaint = tk.Button(row2, text="💾 另存消除後檔案", font=("Microsoft JhengHei UI", 9), bg="#e2e8f0", relief="groove", padx=8, pady=3, state="disabled", command=self.save_inpaint_result)
        self.btn_save_inpaint.pack(side="left", padx=(0, 6))

        self.btn_send_ai = tk.Button(row2, text="🚀 傳送至 AI 放大修復", font=("Microsoft JhengHei UI", 9, "bold"), bg="#10b981", fg="#ffffff", activebackground="#059669", relief="flat", padx=10, pady=3, state="disabled", cursor="hand2", command=self.send_to_ai_tab)
        self.btn_send_ai.pack(side="left", padx=(0, 10))

        tk.Label(row2, text="💡 提示：左鍵塗抹 | 滾輪/按鈕縮放 | 右鍵按住拖曳平移", font=("Microsoft JhengHei UI", 8), bg="#f4f5f7", fg="#64748b").pack(side="right")

        canvas_frame = tk.Frame(self.tab_inpaint, bg="#1e2638")
        canvas_frame.pack(fill="both", expand=True, pady=4)

        self.canvas = tk.Canvas(canvas_frame, bg="#1e2638", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<Button-1>", self.on_paint_start)
        self.canvas.bind("<B1-Motion>", self.on_paint_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_paint_end)
        self.canvas.bind("<Button-3>", self.on_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_pan_move)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.draw_placeholder()

    # ==================== 縮放與平移核心 ====================
    def zoom_in(self):
        if not self.display_image: return
        self.user_zoom = min(5.0, round(self.user_zoom * 1.25, 2))
        self.redraw_canvas_image()

    def zoom_out(self):
        if not self.display_image: return
        self.user_zoom = max(0.5, round(self.user_zoom / 1.25, 2))
        self.redraw_canvas_image()

    def zoom_reset(self):
        if not self.display_image: return
        self.user_zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.redraw_canvas_image()

    def on_mouse_wheel(self, event):
        if not self.display_image: return
        if event.delta > 0: self.zoom_in()
        else: self.zoom_out()

    def on_pan_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_pan_move(self, event):
        if not self.display_image: return
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.pan_x += dx
        self.pan_y += dy
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.redraw_canvas_image()

    def update_brush_label(self, val):
        self.lbl_brush_val.config(text=f"{int(float(val))}px")

    def draw_placeholder(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 600
        h = self.canvas.winfo_height() or 260
        text = "🖼️ 請點擊上方「📁 開啟檔案」載入圖片或影片\n以滑鼠左鍵塗抹覆蓋欲消除之浮水印\n(支援滑鼠滾輪放大與右鍵拖曳平移)"
        self.canvas.create_text(w // 2, h // 2, text=text, fill="#94a3b8", font=("Microsoft JhengHei UI", 12), justify="center", tags="placeholder")

    def open_inpaint_file(self):
        f = filedialog.askopenfilename(
            title="選擇要消除浮水印的圖片或影片",
            filetypes=[("媒體檔案", "*.mp4 *.mkv *.avi *.mov *.jpg *.jpeg *.png *.webp *.bmp"), ("所有檔案", "*.*")]
        )
        if not f: return

        self.inpaint_file = Path(f)
        self.log(f"已載入待消除浮水印檔案: {self.inpaint_file.name}")
        self.zoom_reset()
        self.load_media_preview(self.inpaint_file)
        self.clear_mask()
        self.btn_save_inpaint.config(state="disabled")
        self.btn_send_ai.config(state="disabled")

    def load_media_preview(self, filepath):
        ffmpeg, _, _ = get_binaries()
        img_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        preview_path = filepath

        if filepath.suffix.lower() not in img_exts:
            tmp_preview = BASE_DIR / "temp_preview.jpg"
            if ffmpeg:
                cmd = [ffmpeg, "-y", "-ss", "00:00:01", "-i", str(filepath), "-vframes", "1", "-q:v", "2", str(tmp_preview)]
                subprocess.run(cmd, creationflags=CREATE_NO_WINDOW)
                if not tmp_preview.exists():
                    cmd = [ffmpeg, "-y", "-i", str(filepath), "-vframes", "1", "-q:v", "2", str(tmp_preview)]
                    subprocess.run(cmd, creationflags=CREATE_NO_WINDOW)
                preview_path = tmp_preview

        if HAS_PIL and Path(preview_path).exists():
            try:
                self.display_image = Image.open(preview_path).convert("RGB")
                self.orig_w, self.orig_h = self.display_image.size
                self.redraw_canvas_image()
            except Exception as e:
                self.log(f"載入預覽圖錯誤: {e}")
        else:
            self.orig_w, self.orig_h = (1280, 720)
            self.draw_placeholder()

    def on_canvas_resize(self, event=None):
        if self.display_image:
            self.redraw_canvas_image()
        elif not self.inpaint_file:
            self.draw_placeholder()

    def redraw_canvas_image(self):
        if not self.display_image or not HAS_PIL: return
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)

        self.base_ratio = min(cw / self.orig_w, ch / self.orig_h)
        total_scale = self.base_ratio * self.user_zoom

        self.disp_w = int(self.orig_w * total_scale)
        self.disp_h = int(self.orig_h * total_scale)
        self.disp_ox = (cw - self.disp_w) // 2 + self.pan_x
        self.disp_oy = (ch - self.disp_h) // 2 + self.pan_y

        self.lbl_zoom.config(text=f"{int(self.user_zoom * 100)}%")

        resized = self.display_image.resize((self.disp_w, self.disp_h), Image.Resampling.BILINEAR)
        self.display_photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(self.disp_ox, self.disp_oy, anchor="nw", image=self.display_photo, tags="bg_img")

        for stroke in self.undo_stack:
            for item in stroke:
                rx, ry, rr = item["orig_coord"]
                cx = self.disp_ox + rx * total_scale
                cy = self.disp_oy + ry * total_scale
                cr = rr * total_scale
                obj_id = self.canvas.create_oval(cx - cr, cy - cr, cx + cr, cy + cr, fill="#ef4444", outline="#ef4444", stipple="gray50", tags="mask")
                item["id"] = obj_id

    # ==================== 塗抹互動事件 ====================
    def on_paint_start(self, event):
        if not self.display_image: return
        self.current_stroke = []
        self.paint_at(event.x, event.y)

    def on_paint_move(self, event):
        if not self.display_image: return
        self.paint_at(event.x, event.y)

    def on_paint_end(self, event):
        if self.current_stroke:
            self.undo_stack.append(self.current_stroke)
            self.current_stroke = []

    def paint_at(self, cx, cy):
        total_scale = self.base_ratio * self.user_zoom
        if total_scale <= 0: return

        rx = (cx - self.disp_ox) / total_scale
        ry = (cy - self.disp_oy) / total_scale
        brush_r = self.brush_size.get() / 2
        orig_r = brush_r / total_scale

        if 0 <= rx <= self.orig_w and 0 <= ry <= self.orig_h:
            obj_id = self.canvas.create_oval(
                cx - brush_r, cy - brush_r, cx + brush_r, cy + brush_r,
                fill="#ef4444", outline="#ef4444", stipple="gray50", tags="mask"
            )
            item = {"id": obj_id, "orig_coord": (rx, ry, orig_r)}
            self.current_stroke.append(item)
            self.mask_boxes.append((rx, ry, orig_r))

    def undo_stroke(self):
        if self.undo_stack:
            last_stroke = self.undo_stack.pop()
            for item in last_stroke:
                self.canvas.delete(item["id"])
                if item["orig_coord"] in self.mask_boxes:
                    self.mask_boxes.remove(item["orig_coord"])
            self.log("已復原上一次筆刷塗抹。")

    def clear_mask(self):
        self.canvas.delete("mask")
        self.undo_stack.clear()
        self.current_stroke.clear()
        self.mask_boxes.clear()
        self.log("已清除所有浮水印標記。")

    def get_mask_bounding_box(self):
        if not self.mask_boxes: return None
        min_x = min(x - r for x, y, r in self.mask_boxes)
        max_x = max(x + r for x, y, r in self.mask_boxes)
        min_y = min(y - r for x, y, r in self.mask_boxes)
        max_y = max(y + r for x, y, r in self.mask_boxes)

        min_x = max(0, int(min_x))
        min_y = max(0, int(min_y))
        w = max(10, min(self.orig_w - min_x, int(max_x - min_x)))
        h = max(10, min(self.orig_h - min_y, int(max_y - min_y)))
        return min_x, min_y, w, h

    def start_inpaint_process(self):
        if self.is_processing: return
        if not self.inpaint_file or not self.inpaint_file.exists():
            messagebox.showwarning("提示", "請先點擊「開啟檔案」載入影像！")
            return
        if not self.mask_boxes:
            messagebox.showwarning("提示", "請在畫面浮水印區域上塗抹紅色標記！")
            return

        ffmpeg, _, _ = get_binaries()
        if not ffmpeg:
            messagebox.showerror("錯誤", "需要 FFmpeg 支援！")
            return

        self.is_processing = True
        self.cancel_requested = False
        self.btn_run_inpaint.config(state="disabled", text="⏳ 正在消除中...")
        self.progressbar["value"] = 0
        self.lbl_pct.config(text="處理中...")

        threading.Thread(target=self.inpaint_task, daemon=True).start()

    def inpaint_task(self):
        ffmpeg, _, _ = get_binaries()
        bbox = self.get_mask_bounding_box()
        x, y, w, h = bbox
        self.log(f"浮水印塗抹範圍: X={x}, Y={y}, 寬={w}, 高={h}")

        src = self.inpaint_file
        self.last_output_dir = src.parent
        dst = src.with_name(f"{src.stem}_delogo{src.suffix}")
        img_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

        try:
            delogo_vf = f"delogo=x={x}:y={y}:w={w}:h={h}"
            if src.suffix.lower() in img_exts:
                self.lbl_info.config(text="正在消除圖片浮水印...")
                self.log(f"▶ 正在消除圖片浮水印: {src.name}")
                cmd = [ffmpeg, "-y", "-i", str(src), "-vf", delogo_vf, str(dst)]
                self.run_subproc(cmd)
            else:
                self.lbl_info.config(text="正在消除影片浮水印...")
                self.log(f"▶ 正在消除影片浮水印 (FFmpeg Delogo): {src.name}")
                cmd = [
                    ffmpeg, "-y", "-i", str(src), "-vf", delogo_vf,
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy", str(dst)
                ]
                self.run_subproc(cmd)

            self.progressbar["value"] = 100
            self.lbl_pct.config(text="100%")
            self.lbl_info.config(text="🎉 浮水印消除完成！")
            self.log(f"✔ 浮水印消除完成！成果儲存至: {dst.name}")

            self.last_clean_result = dst
            self.btn_save_inpaint.config(state="normal")
            self.btn_send_ai.config(state="normal")

            self.load_media_preview(dst)
            self.clear_mask()
            messagebox.showinfo("完成", f"浮水印消除完成！\n已即時更新畫面預覽。\n檔案已儲存至：{dst.name}")
        except Exception as e:
            self.log(f"消除浮水印失敗: {e}")
            messagebox.showerror("錯誤", f"處理失敗：\n{e}")
        finally:
            self.is_processing = False
            self.btn_run_inpaint.config(state="normal", text="✨ 立即消除浮水印")

    def save_inpaint_result(self):
        if not self.last_clean_result or not self.last_clean_result.exists(): return
        dst_save = filedialog.asksaveasfilename(
            initialfile=self.last_clean_result.name,
            defaultextension=self.last_clean_result.suffix,
            filetypes=[("媒體檔案", f"*{self.last_clean_result.suffix}")]
        )
        if dst_save:
            shutil.copyfile(self.last_clean_result, dst_save)
            messagebox.showinfo("另存完成", f"已成功儲存至：\n{dst_save}")

    def send_to_ai_tab(self):
        if not self.last_clean_result or not self.last_clean_result.exists(): return
        p = str(self.last_clean_result.resolve())
        items = list(self.listbox_enh.get(0, "end"))
        if p not in items:
            self.listbox_enh.insert("end", p)
        self.notebook.select(self.tab_enhance)
        self.log(f"已將消除浮水印後的檔案傳送至「AI 畫質修復」清單: {self.last_clean_result.name}")
        self.analyze_enh_file(p)
        messagebox.showinfo("已傳送", "已自動切換至「AI 畫質修復」頁面！\n您可直接選擇模型並開始 4x 超解析度放大。")

    # ==================== 共用處理邏輯 ====================
    def log(self, text: str):
        now_str = datetime.now().strftime("%H:%M:%S")
        line = f"[{now_str}] {text}\n"
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", line)
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def update_engine_status(self):
        ffmpeg, ffprobe, esrgan = get_binaries()
        if esrgan and ffmpeg:
            self.lbl_status_engine.config(text="🟢 AI 引擎已就緒：realesrgan-ncnn-vulkan.exe (支援 FFmpeg)", fg="#16a34a")
            self.btn_install.config(text="☑ AI 引擎已就緒", bg="#e2e8f0", fg="#334155", state="disabled")
        elif esrgan:
            self.lbl_status_engine.config(text="🟡 影像核心已就緒 (需安裝 FFmpeg 支援影片)", fg="#ca8a04")
            self.btn_install.config(text="⬇️ 安裝 FFmpeg 支援", bg="#fef08a", fg="#854d0e", state="normal")
        else:
            self.lbl_status_engine.config(text="🔴 尚未安裝 AI 核心組件 (可點擊下方按鈕安裝)", fg="#dc2626")
            self.btn_install.config(text="⬇️ 一鍵安裝 AI 引擎", bg="#dbeafe", fg="#1d4ed8", state="normal")

    def start_install_engine(self):
        if self.is_installing: return
        self.is_installing = True
        self.btn_install.config(state="disabled", text="⏳ 下載安裝中...")
        self.log("開始自動下載與部署 AI 引擎核心...")
        threading.Thread(target=self.install_engine_task, daemon=True).start()

    def install_engine_task(self):
        ffmpeg, ffprobe, esrgan = get_binaries()
        try:
            if not esrgan:
                self.log("正在連線下載 Real-ESRGAN-ncnn-vulkan (約 20MB)...")
                req = urllib.request.Request(ESRGAN_URL, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    data = bytearray()
                    while chunk := resp.read(1024 * 64):
                        data.extend(chunk)
                        if total:
                            pct = int(len(data) / total * 100)
                            self.progressbar["value"] = pct
                            self.lbl_pct.config(text=f"{pct}%")
                            self.lbl_info.config(text=f"下載 Real-ESRGAN 進度...")

                CORE_DIR.mkdir(parents=True, exist_ok=True)
                self.log("下載完成，正在解壓縮 AI 核心至 core/...")
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    z.extractall(CORE_DIR)
                self.log("Real-ESRGAN 核心已成功安裝！")

            ffmpeg, ffprobe, esrgan = get_binaries()
            if not ffmpeg or not ffprobe:
                self.log("正在下載 FFmpeg 影片引擎 (約 90MB)...")
                req = urllib.request.Request(FFMPEG_URL, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    data = bytearray()
                    while chunk := resp.read(1024 * 128):
                        data.extend(chunk)
                        if total:
                            pct = int(len(data) / total * 100)
                            self.progressbar["value"] = pct
                            self.lbl_pct.config(text=f"{pct}%")
                            self.lbl_info.config(text=f"下載 FFmpeg: {len(data)//1024//1024}MB / {total//1024//1024}MB")

                self.log("正在解壓縮部署 FFmpeg 與 FFprobe 至 core/...")
                CORE_DIR.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    for member in z.namelist():
                        if member.endswith("ffmpeg.exe"):
                            with z.open(member) as src, open(CORE_DIR / "ffmpeg.exe", "wb") as dst:
                                shutil.copyfileobj(src, dst)
                        elif member.endswith("ffprobe.exe"):
                            with z.open(member) as src, open(CORE_DIR / "ffprobe.exe", "wb") as dst:
                                shutil.copyfileobj(src, dst)
                self.log("FFmpeg 引擎已成功安裝！")

            self.progressbar["value"] = 100
            self.lbl_pct.config(text="100%")
            self.lbl_info.config(text="🎉 AI 核心與影片引擎已全數安裝完成！")
            self.log("所有核心組件已部署完畢，現在可直接修復影片。")
            messagebox.showinfo("成功", "AI 核心與影片引擎已自動安裝就緒！")
        except Exception as e:
            self.log(f"❌ 安裝失敗: {e}")
            messagebox.showerror("錯誤", f"自動下載安裝時發生錯誤：\n{e}")
        finally:
            self.is_installing = False
            self.update_engine_status()

    def add_files_enh(self):
        exts = "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.jpg *.jpeg *.png *.webp *.bmp"
        files = filedialog.askopenfilenames(title="選擇要修復的檔案", filetypes=[("支援的媒體檔案", exts), ("所有檔案", "*.*")])
        if files:
            current_items = list(self.listbox_enh.get(0, "end"))
            for f in files:
                p = str(Path(f).resolve())
                if p not in current_items:
                    self.listbox_enh.insert("end", p)
            self.lbl_info.config(text=f"清單共有 {self.listbox_enh.size()} 個待處理項目")
            self.log(f"已新增 {len(files)} 個檔案至修復清單。")
            # 自動分析並預覽最後加入的第一個檔案
            self.analyze_enh_file(files[0])

    def clear_files_enh(self):
        self.listbox_enh.delete(0, "end")
        self.progressbar["value"] = 0
        self.lbl_pct.config(text="")
        self.lbl_info.config(text="已清空清單")
        self.lbl_spec_file.config(text="請在上方清單中點選檔案以查看規格分析")
        self.lbl_spec_res.config(text="• 原始尺寸：--- ➔ 預計輸出尺寸：---")
        self.lbl_spec_fps.config(text="• 影格速率 (FPS)：--- | 檔案大小：---")
        self.lbl_enh_thumb.config(image="", text="無預覽")
        self.log("已清空修復清單。")

    def open_output_dir(self):
        target = self.last_output_dir if self.last_output_dir.exists() else BASE_DIR
        os.startfile(str(target))

    def cancel_process(self):
        if self.is_processing:
            self.cancel_requested = True
            self.log("⚠️ 已觸發取消！正在強制終止背景程序並釋放 GPU...")
            if self.current_process:
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)], creationflags=CREATE_NO_WINDOW)
                except Exception:
                    pass
            self.btn_cancel_enh.config(state="disabled", text="正在取消...")

    def run_subproc(self, cmd):
        if self.cancel_requested: raise InterruptedError("使用者已手動取消")
        self.current_process = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
        ret = self.current_process.wait()
        self.current_process = None
        if self.cancel_requested: raise InterruptedError("使用者已手動取消")
        if ret != 0: raise subprocess.CalledProcessError(ret, cmd)

    def start_enhance_process(self):
        if self.is_processing: return
        items = list(self.listbox_enh.get(0, "end"))
        if not items:
            messagebox.showwarning("提示", "請先選擇待修復的檔案！")
            return

        ffmpeg, ffprobe, esrgan = get_binaries()
        if not esrgan:
            if messagebox.askyesno("尚未安裝核心", "檢測到尚未安裝 Real-ESRGAN AI 核心！\n是否立即自動下載並安裝？"):
                self.start_install_engine()
            return
        if not ffmpeg or not ffprobe:
            messagebox.showerror("錯誤", "需要 FFmpeg 支援！")
            return

        self.is_processing = True
        self.cancel_requested = False
        self.btn_start_enh.config(state="disabled", text="⏳ 正在修復中...")
        self.btn_cancel_enh.config(state="normal", text="🛑 取消修復", bg="#ef4444", fg="#ffffff")
        self.progressbar["value"] = 0
        self.lbl_pct.config(text="0%")

        threading.Thread(target=self.enhance_queue_task, args=(items,), daemon=True).start()

    def enhance_queue_task(self, file_items):
        ffmpeg, ffprobe, esrgan = get_binaries()
        model_name = self.model_map.get(self.var_model.get(), "realesrgan-x4plus")
        scale = int(self.var_scale.get())

        total = len(file_items)
        img_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        self.log(f"開始 AI 畫質修復，共 {total} 個檔案 (模型: {model_name}, 倍率: {scale}x)...")

        cancelled = False
        for idx, item_path in enumerate(file_items):
            if self.cancel_requested:
                cancelled = True
                break

            src = Path(item_path)
            self.last_output_dir = src.parent
            dst = src.with_name(f"{src.stem}_enhanced_{scale}x{src.suffix}")
            self.lbl_info.config(text=f"({idx+1}/{total}) 準備處理: {src.name}")
            self.log(f"▶ 正在處理 [{idx+1}/{total}]: {src.name}")

            try:
                if src.suffix.lower() in img_exts:
                    m_dir = Path(esrgan).parent / "models"
                    m_opt = ["-m", str(m_dir)] if m_dir.exists() else []
                    cmd = [esrgan, "-i", str(src), "-o", str(dst), "-n", model_name, "-s", str(scale)] + m_opt
                    self.lbl_info.config(text=f"({idx+1}/{total}) AI 圖片放大中...")
                    self.log(f"  └ 正在進行 Real-ESRGAN AI 放大...")
                    self.run_subproc(cmd)
                    pct = int(((idx + 1) / total) * 100)
                    self.progressbar["value"] = pct
                    self.lbl_pct.config(text=f"{pct}%")
                    self.log(f"  ✔ 圖片修復完成: {dst.name}")
                else:
                    fps_cmd = [ffprobe, "-v", "0", "-of", "csv=p=0", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", str(src)]
                    fps = subprocess.check_output(fps_cmd, text=True, creationflags=CREATE_NO_WINDOW).strip()

                    with tempfile.TemporaryDirectory() as tmp:
                        raw_dir = Path(tmp) / "raw"
                        out_dir = Path(tmp) / "out"
                        raw_dir.mkdir(); out_dir.mkdir()

                        self.lbl_info.config(text=f"({idx+1}/{total}) [1/3 拆幀] {src.name}")
                        self.lbl_pct.config(text="拆幀中...")
                        self.log(f"  └ [1/3 拆幀] 正在解構視訊幀...")
                        self.run_subproc([ffmpeg, "-i", str(src), "-qscale:v", "2", str(raw_dir / "%08d.png")])

                        total_frames = len(list(raw_dir.glob("*.png")))
                        self.log(f"  └ 拆幀完成！共 {total_frames} 幀，開始 GPU 逐幀超解析度修復...")

                        stop_monitor = threading.Event()
                        def monitor_frames():
                            last_reported_pct = -1
                            while not stop_monitor.is_set():
                                if total_frames > 0:
                                    done = len(list(out_dir.glob("*.png")))
                                    pct = int((done / total_frames) * 100)
                                    self.progressbar["value"] = pct
                                    self.lbl_pct.config(text=f"{pct}% ({done}/{total_frames})")
                                    self.lbl_info.config(text=f"({idx+1}/{total}) [2/3 AI 放大] {done}/{total_frames} 幀 ⚡ GPU 運算中...")
                                    if pct >= last_reported_pct + 10 and done > 0:
                                        last_reported_pct = (pct // 10) * 10
                                        self.log(f"  └ AI 放大進度: {done}/{total_frames} 幀 ({pct}%)")
                                time.sleep(0.3)

                        t_mon = threading.Thread(target=monitor_frames, daemon=True)
                        t_mon.start()

                        try:
                            m_dir = Path(esrgan).parent / "models"
                            m_opt = ["-m", str(m_dir)] if m_dir.exists() else []
                            self.run_subproc([esrgan, "-i", str(raw_dir), "-o", str(out_dir), "-n", model_name, "-s", str(scale)] + m_opt)
                        finally:
                            stop_monitor.set()
                            t_mon.join(timeout=1.0)

                        if self.cancel_requested: raise InterruptedError("使用者已手動取消")

                        self.progressbar["value"] = 98
                        self.lbl_pct.config(text="98%")
                        self.lbl_info.config(text=f"({idx+1}/{total}) [3/3 音畫合成中] {src.name}")
                        self.log(f"  └ [3/3 音畫合成] AI 放大完成，正在封裝影像融合原音訊...")

                        self.run_subproc([
                            ffmpeg, "-y", "-r", fps, "-i", str(out_dir / "%08d.png"), "-i", str(src),
                            "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", str(dst)
                        ])
                        self.log(f"  ✔ 影片修復完成: {dst.name}")

            except InterruptedError:
                cancelled = True
                break
            except Exception as e:
                self.log(f"  ❌ 處理中斷或失敗: {e}")

        if cancelled:
            self.lbl_info.config(text="⚠️ 已成功中斷並取消任務。")
            self.lbl_pct.config(text="已取消")
            self.progressbar["value"] = 0
            self.log("🛑 任務已被使用者強制中途取消！已秒級釋放 GPU 與清理暫存。")
            messagebox.showwarning("已取消", "處理程序已成功中途取消，GPU 資源已釋放。")
        else:
            self.progressbar["value"] = 100
            self.lbl_pct.config(text="100%")
            self.lbl_info.config(text=f"🎉 全部 {total} 個檔案修復完成！")
            self.log(f"🎉 任務完成！所有修復檔案已儲存完畢。")
            messagebox.showinfo("完成", f"全部 {total} 個檔案已修復完成！\n可點擊「開啟資料夾」查看結果。")

        self.is_processing = False
        self.cancel_requested = False
        self.btn_start_enh.config(state="normal", text="🚀 開始 AI 畫質修復")
        self.btn_cancel_enh.config(state="disabled", text="🛑 取消修復", bg="#fee2e2", fg="#991b1b")

if __name__ == "__main__":
    app = VideoAiApp()
    app.mainloop()
