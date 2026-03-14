import os
from PIL import Image, ImageDraw, ImageFont

# --- 必须确保这些常量在 utils.py 的全局作用域内 ---
COLOR_BG = (43, 45, 49)        # 背景深灰
COLOR_HEADER = (18, 18, 19)     # 表头黑色
COLOR_CORRECT = (83, 141, 78)   # 绿色
COLOR_WRONG = (186, 73, 73)     # 红色
COLOR_UNKNOWN = (110, 110, 110) # 灰色
COLOR_TEXT = (255, 255, 255)    # 白色文字
COLOR_BORDER = (60, 60, 60)     # 边框

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_PATH, "STZHONGS.TTF") 

def get_font(size):
    try:
        if os.path.exists(FONT_PATH):
            return ImageFont.truetype(FONT_PATH, size)
    except:
        pass
    return ImageFont.load_default()

def compare_attributes(guess_name, target_name, operators):
    # ... (之前的逻辑不变) ...
    guess_info = operators[guess_name]
    target_info = operators[target_name]
    attrs = ["性别", "种族", "星级", "职业", "分支", "阵营", "组织", "国家"]
    row = [{"value": guess_name, "status": "name"}]
    for attr in attrs:
        g_val = str(guess_info.get(attr, "未知"))
        t_val = str(target_info.get(attr, "未知"))
        if g_val in ["未知", "未公开", "None", ""]:
            row.append({"value": "未知", "status": "unknown"})
        elif attr == "星级":
            g_s = int(g_val) if g_val.isdigit() else 0
            t_s = int(t_val) if t_val.isdigit() else 0
            if g_s == t_s:
                row.append({"value": g_val, "status": "correct"})
            else:
                row.append({"value": f"{g_val}{'<' if g_s < t_s else '>'}", "status": "incorrect"})
        else:
            row.append({"value": g_val, "status": "correct" if g_val == t_val else "incorrect"})
    return row

def render_table(history, output_path):
    if not history: return
    
    cell_width, cell_height = 110, 60
    padding, header_height = 20, 60
    columns = ["干员名", "性别", "种族", "星级", "职业", "分支", "阵营", "组织", "国家"]
    
    img_width = len(columns) * cell_width + padding * 2
    img_height = header_height + len(history) * cell_height + padding * 2

    # --- 这里的 COLOR_BG 必须是上面定义的那个 ---
    img = Image.new('RGB', (img_width, img_height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    font = get_font(20)

    # 绘制表头
    for i, col in enumerate(columns):
        x0, y0 = padding + i * cell_width, padding
        x1, y1 = x0 + cell_width, y0 + header_height
        draw.rectangle([x0, y0, x1, y1], fill=COLOR_HEADER, outline=COLOR_BORDER)
        bbox = draw.textbbox((0, 0), col, font=font)
        draw.text((x0 + (cell_width - (bbox[2]-bbox[0]))/2, y0 + (header_height - (bbox[3]-bbox[1]))/2 - 4), col, font=font, fill=COLOR_TEXT)

    # 绘制行
    for row_idx, row_data in enumerate(history):
        for col_idx, cell in enumerate(row_data):
            x0 = padding + col_idx * cell_width
            y0 = padding + header_height + row_idx * cell_height
            x1, y1 = x0 + cell_width, y0 + cell_height
            
            status, val = cell["status"], str(cell["value"])
            bg_color = COLOR_BG
            show_text, display_val = False, ""

            if status == "name":
                bg_color = (30, 30, 30); show_text = True; display_val = val
            elif status == "correct":
                bg_color = COLOR_CORRECT
            elif status == "unknown":
                bg_color = COLOR_UNKNOWN
            elif status == "incorrect":
                bg_color = COLOR_WRONG
                if columns[col_idx] == "星级":
                    show_text = True; display_val = val[-1]

            draw.rectangle([x0, y0, x1, y1], fill=bg_color, outline=COLOR_BORDER)
            if show_text and display_val:
                bbox = draw.textbbox((0, 0), display_val, font=font)
                draw.text((x0 + (cell_width - (bbox[2]-bbox[0]))/2, y0 + (cell_height - (bbox[3]-bbox[1]))/2 - 4), display_val, font=font, fill=COLOR_TEXT)

    img.save(output_path)
    return output_path
