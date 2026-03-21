import os
from PIL import Image, ImageDraw, ImageFont

# --- 视觉常量定义 ---
COLOR_BG = (211, 211, 211)        # 纯灰色背景
COLOR_HEADER = (180, 180, 180)    # 稍深的表头灰色
COLOR_TEXT = (50, 50, 50)         # 深色文字
COLOR_LINE = (190, 190, 190)      # 分割线
CANVAS_W = 406
CANVAS_H = 220

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = os.path.join(BASE_PATH, "resource")
# 字体文件名
FONT_FILENAME = "STZHONGS.TTF"

def get_font(size):
    """ 优先加载同级目录下的 STZHONGS.TTF """
    local_font = os.path.join(BASE_PATH, FONT_FILENAME)
    if os.path.exists(local_font):
        try:
            return ImageFont.truetype(local_font, size)
        except:
            pass
    
    # 备选系统字体
    fonts = ["msyh.ttc", "simhei.ttf", "SimSun.ttc"]
    for f in fonts:
        try: return ImageFont.truetype(f, size)
        except: continue
    return ImageFont.load_default()

def get_force_set(op_data):
    forces = set()
    for k in ["阵营", "组织", "国家"]:
        val = op_data.get(k, "未知")
        if val and str(val).strip() and val != "未知":
            forces.add(str(val).strip())
    return forces

def compare_attributes(guess_name, target_name, ops):
    g, t = ops[guess_name], ops[target_name]
    row = []
    # 基础 4 项 (性别, 种族, 职业, 分支)
    for col in ["性别", "种族", "职业", "分支"]:
        gv, tv = str(g.get(col, "未知")), str(t.get(col, "未知"))
        icon = "thumbs-up.png" if gv == tv else "thumbs-down.png"
        if "未知" in [gv, tv]: icon = "unknown.png"
        row.append({"val": None, "icon": icon})
    # 星级 (hand-up/down)
    try:
        gs = int(str(g.get("星级", 0)).strip())
        ts = int(str(t.get("星级", 0)).strip())
    except: gs, ts = 0, 0
    s_icon = "thumbs-up.png" if gs == ts else ("hand-up.png" if gs < ts else "hand-down.png")
    row.insert(2, {"val": None, "icon": s_icon})
    # 位置
    gp, tp = g.get("位置", "未知"), t.get("位置", "未知")
    p_icon = "thumbs-up.png" if gp == tp else ("unknown.png" if "近战/远程" in [gp, tp] else "thumbs-down.png")
    row.insert(5, {"val": None, "icon": p_icon})
    # 势力
    gf, tf = get_force_set(g), get_force_set(t)
    f_icon = "thumbs-up.png" if gf == tf else ("unknown.png" if gf & tf else "thumbs-down.png")
    row.append({"val": None, "icon": f_icon})
    # 首列
    row.insert(0, {"val": guess_name, "icon": None})
    return row

def render_table(history_data, output_path):
    headers = ["干员名", "性别", "种族", "星级", "职业", "分支", "位置", "势力"]
    name_col_w = 85
    other_col_w = (CANVAS_W - name_col_w) // (len(headers) - 1)
    header_h, row_h, icon_size = 30, 23, 18
    
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), COLOR_BG)
    draw = ImageDraw.Draw(img)
    font_main = get_font(16)
    font_header = get_font(14)

    # 1. 绘制表头 (统一对齐线)
    draw.rectangle([0, 0, CANVAS_W, header_h], fill=COLOR_HEADER)
    header_text_y = (header_h - 14) // 2 - 1 
    for i, h in enumerate(headers):
        x = 0 if i == 0 else name_col_w + (i - 1) * other_col_w
        curr_w = name_col_w if i == 0 else other_col_w
        bw = draw.textbbox((0, 0), h, font=font_header)
        draw.text((x + (curr_w-(bw[2]-bw[0]))//2, header_text_y), h, font=font_header, fill=COLOR_TEXT)

    # 2. 绘制记录 (最多展示 8 条)
    display_data = history_data[-8:] 
    for r_idx, r_data in enumerate(display_data):
        y = header_h + r_idx * row_h
        row_text_y = y + (row_h - 16) // 2 - 1
        for c_idx, cell in enumerate(r_data):
            x = 0 if c_idx == 0 else name_col_w + (c_idx - 1) * other_col_w
            curr_w = name_col_w if c_idx == 0 else other_col_w
            if cell["val"]:
                draw.text((x + 6, row_text_y), cell["val"], font=font_main, fill=COLOR_TEXT)
            elif cell["icon"]:
                i_path = os.path.join(RESOURCE_DIR, cell["icon"])
                if os.path.exists(i_path):
                    try:
                        icon = Image.open(i_path).convert("RGBA").resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                        img.paste(icon, (x + (curr_w-icon_size)//2, y + (row_h-icon_size)//2), icon)
                    except: pass
        draw.line([(0, y + row_h), (CANVAS_W, y + row_h)], fill=COLOR_LINE, width=1)

    img.save(output_path)