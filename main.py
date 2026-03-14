import os
import json
import random
import logging
from astrbot.api.all import *
from .utils import compare_attributes, render_table

logger = logging.getLogger("astrbot")

@register("arknights_guess", "YourName", "明日方舟猜猜乐游戏", "1.0.0")
class ArknightsGuessPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 动态获取 main.py 所在的文件夹绝对路径
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 修改点：去掉 assets，直接指向根目录
        data_path = os.path.join(self.plugin_dir, "arknights_full_data.json")
        
        self.operators = {}
        self.sessions = {}

        try:
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    self.operators = json.load(f)
                logger.info(f"成功加载 {len(self.operators)} 名干员数据。")
            else:
                logger.error(f"找不到数据文件，请检查路径: {data_path}")
        except Exception as e:
            logger.error(f"加载数据出错: {e}")

    @command("方舟猜猜乐")
    async def start_game(self, event: AstrMessageEvent):
        '''开始一局明日方舟干员猜猜乐'''
        if not self.operators:
            yield event.plain_result("❌ 插件数据加载失败，请检查根目录是否有 json 文件。")
            return

        session_id = event.get_session_id()
        target_name = random.choice(list(self.operators.keys()))
        
        self.sessions[session_id] = {
            "target": target_name,
            "history": [],
            "tries": 0
        }
        
        yield event.plain_result(f"🎮 游戏开始！我已经选好了一名干员。\n请直接发送干员名称进行猜测（8次机会）。")

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id not in self.sessions:
            return

        # 获取用户输入
        try:
            user_input = event.message_str.strip()
        except:
            user_input = event.get_plain_text().strip() if hasattr(event, 'get_plain_text') else ""
        
        # 必须是有效干员才继续
        if not user_input or user_input not in self.operators:
            return 

        # --- 核心修复点：确保变量已定义 ---
        session = self.sessions[session_id]
        target_name = session["target"] # <--- 确保这一行存在
        # -------------------------------

        # 1. 对比属性
        row_data = compare_attributes(user_input, target_name, self.operators)
        session["history"].append(row_data)
        session["tries"] += 1
        
        # 2. 绘图
        img_name = f"temp_{session_id}.png"
        img_path = os.path.join(self.plugin_dir, img_name)
        
        try:
            render_table(session["history"], img_path)
            yield event.image_result(img_path)
        except Exception as e:
            logger.error(f"绘图失败: {e}")
            yield event.plain_result(f"❌ 绘图失败，请联系管理员查看后台日志。")
            return
        
        # 3. 结果判定
        if user_input == target_name:
            urls = self.operators[target_name].get("original_url", [])
            yield event.plain_result(f"🎉 恭喜猜中！答案是：{target_name}")
            if urls: 
                yield event.image_result(random.choice(urls))
            del self.sessions[session_id]
        elif session["tries"] >= 8:
            yield event.plain_result(f"💀 机会用尽！答案是：{target_name}")
            urls = self.operators[target_name].get("original_url", [])
            if urls: 
                yield event.image_result(random.choice(urls))
            del self.sessions[session_id]
