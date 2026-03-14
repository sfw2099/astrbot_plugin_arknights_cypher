import os
from PIL import Image, ImageDraw, ImageFont

# 获取当前文件所在目录
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# 修改点：去掉 assets，直接从 BASE_PATH 获取
FONT_PATH = os.path.join(BASE_PATH, "STZHONGS.TTF") 

def get_font(size):
    try:
        # 再次确认文件名大小写
        if os.path.exists(FONT_PATH):
            return ImageFont.truetype(FONT_PATH, size)
        else:
            # 兼容性：如果全大写找不到，尝试全小写
            alt_path = os.path.join(BASE_PATH, "stzhongs.ttf")
            if os.path.exists(alt_path):
                return ImageFont.truetype(alt_path, size)
    except:
        pass
    return ImageFont.load_default()

def compare_attributes(guess_name, target_name, operators):
    """
    对比猜测干员与目标干员的属性
    返回格式：[{"value": "名称", "status": "name"}, {"value": "属性值", "status": "correct/incorrect/unknown"}, ...]
    """
    guess_info = operators[guess_name]
    target_info = operators[target_name]
    
    # 按照要求的顺序进行对比
    attrs = ["性别", "种族", "星级", "职业", "分支", "阵营", "组织", "国家"]
    row = [{"value": guess_name, "status": "name"}]
    
    for attr in attrs:
        g_val = str(guess_info.get(attr, "未知"))
        t_val = str(target_info.get(attr, "未知"))
        
        # 1. 如果玩家猜测的干员该属性为未知，则直接显示未知
        if g_val in ["未知", "未公开", "None", ""]:
            row.append({"value": "未知", "status": "unknown"})
        
        # 2. 星级特殊处理（显示大于小于号）
        elif attr == "星级":
            g_s = int(g_val) if g_val.isdigit() else 0
            t_s = int(t_val) if t_val.isdigit() else 0
            if g_s == t_s:
                row.append({"value": g_val, "status": "correct"})
            else:
                sign = "<" if g_s < t_s else ">"
                row.append({"value": f"{g_val}{sign}", "status": "incorrect"})
        
        # 3. 其他常规属性对比
        else:
            status = "correct" if g_val == t_val else "incorrect"
            row.append({"value": g_val, "status": status})
            
    return row

def render_table(history, output_path):
    """
    将游戏历史绘制为图片反馈
    """
    if not history:
        return None
    
    # 布局配置
    cell_width = 110
    cell_height = 60
    padding = 20
    header_height = 60
    columns = ["干员名", "性别", "种族", "星级", "职业", "分支", "阵营", "组织", "国家"]
    
    # 计算画布尺寸
    img_width = len(columns) * cell_width + padding * 2
    img_height = header_height + len(history) * cell_height + padding * 2

    # 创建背景
    img = Image.new('RGB', (img_width, img_height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    font = get_font(20)

    # 绘制表头
    for i, col in enumerate(columns):
        x0 = padding + i * cell_width
        y0 = padding
        x1, y1 = x0 + cell_width, y0 + header_height
        draw.rectangle([x0, y0, x1, y1], fill=COLOR_HEADER, outline=COLOR_BORDER)
        
        # 文字居中
        bbox = draw.textbbox((0, 0), col, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x0 + (cell_width - tw) / 2, y0 + (header_height - th) / 2 - 4), col, font=font, fill=COLOR_TEXT)

    # 绘制每一行猜测
    for row_idx, row_data in enumerate(history):
        for col_idx, cell in enumerate(row_data):
            x0 = padding + col_idx * cell_width
            y0 = padding + header_height + row_idx * cell_height
            x1, y1 = x0 + cell_width, y0 + cell_height
            
            status = cell["status"]
            val = str(cell["value"])
            
            bg_color = COLOR_BG
            display_text = ""
            show_text = False

            # 根据你的要求修改绘图逻辑：
            if status == "name":
                bg_color = (30, 30, 30) # 干员名背景略深
                display_text = val
                show_text = True
            elif status == "correct":
                bg_color = COLOR_CORRECT
                show_text = False # 相同直接涂绿，不显示具体文字
            elif status == "unknown":
                bg_color = COLOR_UNKNOWN
                show_text = False # 未知直接涂灰
            elif status == "incorrect":
                bg_color = COLOR_WRONG
                # 星级不同时需要显示大于小于号
                if columns[col_idx] == "星级":
                    display_text = val[-1] # 只取后缀 < 或 >
                    show_text = True
                else:
                    show_text = False # 其他不同直接涂红，不显示文字

            # 画格子
            draw.rectangle([x0, y0, x1, y1], fill=bg_color, outline=COLOR_BORDER)
            
            # 写字
            if show_text and display_text:
                # 处理超长干员名
                if len(display_text) > 5 and status == "name":
                    display_text = display_text[:4] + ".."
                
                bbox = draw.textbbox((0, 0), display_text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw.text((x0 + (cell_width - tw) / 2, y0 + (cell_height - th) / 2 - 4), display_text, font=font, fill=COLOR_TEXT)

    # 保存图片
    img.save(output_path)
    return output_path
