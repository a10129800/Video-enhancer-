import os
from pathlib import Path
from PIL import Image, ImageDraw

def create_app_icon():
    cur = Path(__file__).resolve().parent
    base_dir = cur.parent if cur.name in ["scripts", "src"] else cur
    assets_dir = base_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. 繪製圓角外框底色 (科技藍紫漸變背景)
    # 模擬深藍到電光紫漸層
    for y in range(256):
        ratio = y / 255.0
        r = int(30 * (1 - ratio) + 99 * ratio)
        g = int(27 * (1 - ratio) + 102 * ratio)
        b = int(75 * (1 - ratio) + 241 * ratio)
        draw.line([(24, y), (231, y)], fill=(r, g, b, 255))
        
    # 創建圓角蒙版 (Squircle mask)
    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([20, 20, 235, 235], radius=50, fill=255)
    
    # 將漸變底圖裁切為圓角
    bg = Image.new("RGBA", size, (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask=mask)
    
    draw = ImageDraw.Draw(bg)
    
    # 2. 精緻邊框 (白色微光半透明)
    draw.rounded_rectangle([20, 20, 235, 235], radius=50, outline=(255, 255, 255, 120), width=3)
    draw.rounded_rectangle([23, 23, 232, 232], radius=47, outline=(147, 197, 253, 60), width=2)
    
    # 3. 繪製中央超解析度 AI 璀璨十字星 (四芒星)
    center_x, center_y = 120, 118
    
    def draw_star(cx, cy, r_outer, r_inner, fill_color):
        points = []
        # 4芒星頂點
        points.append((cx, cy - r_outer))                     # 上
        points.append((cx + r_inner * 0.4, cy - r_inner * 0.4))
        points.append((cx + r_outer, cy))                     # 右
        points.append((cx + r_inner * 0.4, cy + r_inner * 0.4))
        points.append((cx, cy + r_outer))                     # 下
        points.append((cx - r_inner * 0.4, cy + r_inner * 0.4))
        points.append((cx - r_outer, cy))                     # 左
        points.append((cx - r_inner * 0.4, cy - r_inner * 0.4))
        draw.polygon(points, fill=fill_color)

    # 主星光芒光暈 (外發光)
    draw_star(center_x, center_y, 76, 16, (96, 165, 250, 100))
    draw_star(center_x, center_y, 68, 14, (192, 132, 252, 160))
    # 主星主體 (亮白到青藍)
    draw_star(center_x, center_y, 60, 12, (255, 255, 255, 255))
    
    # 副星光芒 (右上角小星)
    draw_star(180, 68, 28, 6, (255, 255, 255, 240))
    # 左下角極小微星
    draw_star(66, 175, 18, 4, (147, 197, 253, 220))

    # 4. 底部 "4K" 或 "AI" 徽章標籤
    # 畫一個亮色小膠囊標籤
    badge_x0, badge_y0, badge_x1, badge_y1 = 80, 186, 176, 218
    draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1], radius=16, fill=(16, 185, 129, 230), outline=(255, 255, 255, 180), width=2)
    
    # 標籤上繪製 "4K" 像素文字點陣
    # 簡易粗體筆畫繪製 "4K"
    c_w = (255, 255, 255, 255)
    # 繪製 "4"
    draw.line([(106, 193), (106, 211)], fill=c_w, width=4) # 豎
    draw.line([(96, 193), (96, 203)], fill=c_w, width=4)   # 左豎
    draw.line([(96, 203), (113, 203)], fill=c_w, width=4)  # 橫
    
    # 繪製 "K"
    draw.line([(126, 193), (126, 211)], fill=c_w, width=4) # 主豎
    draw.line([(141, 193), (127, 202)], fill=c_w, width=4) # 右上斜
    draw.line([(127, 202), (142, 211)], fill=c_w, width=4) # 右下斜

    # 儲存 PNG 預覽
    png_path = assets_dir / "app_icon.png"
    bg.save(png_path, "PNG")
    print(f"已儲存 PNG: {png_path}")

    # 儲存全尺寸多層 ICO
    ico_path = assets_dir / "app_icon.ico"
    bg.save(
        ico_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )
    print(f"已儲存 ICO: {ico_path}")
    
    # 根目錄也放一份，方便快捷
    bg.save(base_dir / "app_icon.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])

if __name__ == "__main__":
    create_app_icon()
