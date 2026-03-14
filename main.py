import os
import json
import random
from astrbot.api.all import *
from .utils import compare_attributes, render_table

@register("arknights_guess", "YourName", "明日方舟猜猜乐游戏", "1.0.0")
class ArknightsGuessPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 加载数据
        data_path = os.path.join(os.path.dirname(__file__), "assets", "arknights_full_data.json")
        with open(data_path, 'r', encoding='utf-8') as f:
            self.operators = json.load(f)
        
        # 存储每个会话的游戏状态: { session_id: { "target": "能天使", "history": [] } }
        self.sessions = {}

    @command("方舟猜猜乐")
    async def start_game(self, event: GuildEvent):
        '''开始一局明日方舟干员猜猜乐'''
        session_id = event.get_session_id()
        target_name = random.choice(list(self.operators.keys()))
        
        self.sessions[session_id] = {
            "target": target_name,
            "history": [],
            "tries": 0
        }
        
        yield event.plain_result(f"🎮 游戏开始！我已经选好了一名干员，请直接发送干员名称进行猜测。\n你有 8 次机会。")

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: GuildEvent):
        session_id = event.get_session_id()
        
        # 如果该会话没在游戏中，不理会
        if session_id not in self.sessions:
            return

        user_input = event.get_plain_text().strip()
        
        # 校验是否为干员名
        if user_input not in self.operators:
            return # 或者 yield event.plain_result("数据库没这人")

        session = self.sessions[session_id]
        target_name = session["target"]
        
        # 1. 对比属性
        row_data = compare_attributes(user_input, target_name, self.operators)
        session["history"].append(row_data)
        session["tries"] += 1
        
        # 2. 生成反馈图
        img_path = os.path.join(os.path.dirname(__file__), f"temp_{session_id}.png")
        render_table(session["history"], img_path)
        
        # 3. 发送图片反馈
        yield event.image_result(img_path)
        
        # 4. 胜负判定
        if user_input == target_name:
            # 猜对了，获取随机立绘
            urls = self.operators[target_name].get("original_url", [])
            img_url = random.choice(urls) if urls else None
            
            yield event.plain_result(f"🎉 恭喜！答案正是【{target_name}】！")
            if img_url:
                yield event.image_result(img_url)
            
            del self.sessions[session_id] # 结束游戏
            
        elif session["tries"] >= 8:
            yield event.plain_result(f"💀 机会用尽！正确答案是：{target_name}")
            del self.sessions[session_id]