import os
from PIL import Image, ImageDraw, ImageFont

# --- 1. 颜色与样式常量定义 ---
COLOR_BG = (43, 45, 49)        # 背景深灰
COLOR_HEADER = (18, 18, 19)     # 表头黑色
COLOR_CORRECT = (83, 141, 78)   # 绿色 (完全正确)
COLOR_WRONG = (186, 73, 73)     # 红色 (不匹配)
COLOR_UNKNOWN = (110, 110, 110) # 灰色 (属性未知)
COLOR_TEXT = (255, 255, 255)    # 白色文字
COLOR_BORDER = (60, 60, 60)     # 格子边框颜色

# --- 2. 路径与字体配置 ---
# 动态获取当前文件 (utils.py) 所在的目录
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
# 字体文件直接存放在插件根目录
FONT_PATH = os.path.join(BASE_PATH, "STZHONGS.TTF") 

def get_font(size):
    """ 获取字体对象，具备基础的容错逻辑 """
    try:
        if os.path.exists(FONT_PATH):
            return ImageFont.truetype(FONT_PATH, size)
        else:
            # 如果大写文件名找不到，尝试小写
            alt_path = os.path.join(BASE_PATH, "stzhongs.ttf")
            if os.path.exists(alt_path):
                return ImageFont.truetype(alt_path, size)
    except Exception:
        pass
    # 彻底找不到则返回系统默认（可能不支持中文，但在服务器环境可防止崩溃）
    return ImageFont.load_default()

# --- 3. 逻辑处理函数 ---
def compare_attributes(guess_name, target_name, operators):
    """
    对比猜测干员与目标干员的属性
    返回格式：[{"value": "名称", "status": "name"}, ...]
    """
    guess_info = operators[guess_name]
    target_info = operators[target_name]
    
    # 定义对比维度
    attrs = ["性别", "种族", "星级", "职业", "分支", "阵营", "组织", "国家"]
    row = [{"value": guess_name, "status": "name"}]
    
    for attr in attrs:
        g_val = str(guess_info.get(attr, "未知"))
        t_val = str(target_info.get(attr, "未知"))
        
        # 处理未知项
        if g_val in ["未知", "未公开", "None", ""]:
            row.append({"value": "未知", "status": "unknown"})
        
        # 星级特殊处理：增加 > 或 < 提示
        elif attr == "星级":
            try:
                g_s = int(g_val)
                t_s = int(t_val)
                if g_s == t_s:
                    row.append({"value": g_val, "status": "correct"})
                else:
                    sign = "<" if g_s < t_s else ">"
                    row.append({"value": f"{g_val}{sign}", "status": "incorrect"})
            except:
                row.append({"value": g_val, "status": "incorrect"})
        
        # 其他属性对比
        else:
            status = "correct" if g_val == t_val else "incorrect"
            row.append({"value": g_val, "status": status})
            
    return row

# --- 4. 绘图核心函数 ---
def render_table(history, output_path):
    """
    将游戏历史绘制为图片反馈
    """
    if not history:
        return None
    
    # 布局参数
    cell_width = 110
    cell_height = 60
    padding = 20
    header_height = 60
    columns = ["干员名", "性别", "种族", "星级", "职业", "分支", "阵营", "组织", "国家"]
    
    # 计算画布总尺寸
    img_width = len(columns) * cell_width + padding * 2
    img_height = header_height + len(history) * cell_height + padding * 2

    # 创建画布
    img = Image.new('RGB', (img_width, img_height), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    font = get_font(20)

    # 绘制表头
    for i, col in enumerate(columns):
        x0 = padding + i * cell_width
        y0 = padding
        x1, y1 = x0 + cell_width, y0 + header_height
        
        draw.rectangle([x0, y0, x1, y1], fill=COLOR_HEADER, outline=COLOR_BORDER)
        
        # 文本居中处理
        bbox = draw.textbbox((0, 0), col, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x0 + (cell_width - tw) / 2, y0 + (header_height - th) / 2 - 4), 
                  col, font=font, fill=COLOR_TEXT)

    # 逐行绘制猜测记录
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

            # 根据状态确定颜色与是否显示文字
            if status == "name":
                bg_color = (30, 30, 30) 
                display_text = val
                show_text = True
            elif status == "correct":
                bg_color = COLOR_CORRECT
                show_text = False # 绿色块不显示文字
            elif status == "unknown":
                bg_color = COLOR_UNKNOWN
                show_text = False # 灰色块不显示文字
            elif status == "incorrect":
                bg_color = COLOR_WRONG
                # 仅在星级不匹配时显示 < 或 >
                if columns[col_idx] == "星级":
                    display_text = val[-1] 
                    show_text = True
                else:
                    show_text = False # 其他红色块不显示文字

            # 绘制单元格背景与边框
            draw.rectangle([x0, y0, x1, y1], fill=bg_color, outline=COLOR_BORDER)
            
            # 绘制单元格文字
            if show_text and display_text:
                # 干员名称过长处理
                if len(display_text) > 5 and status == "name":
                    display_text = display_text[:4] + ".."
                
                bbox = draw.textbbox((0, 0), display_text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw.text((x0 + (cell_width - tw) / 2, y0 + (cell_height - th) / 2 - 4), 
                          display_text, font=font, fill=COLOR_TEXT)

    # 保存结果
    img.save(output_path)
    return output_path
