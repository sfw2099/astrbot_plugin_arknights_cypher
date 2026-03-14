import os
import json
import random
from astrbot.api.all import * # 尝试使用这个聚合导入
from .utils import compare_attributes, render_table

@register("arknights_guess", "YourName", "明日方舟猜猜乐游戏", "1.0.0")
class ArknightsGuessPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 加载数据
        data_path = os.path.join(os.path.dirname(__file__), "assets", "arknights_full_data.json")
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                self.operators = json.load(f)
        else:
            self.operators = {}
        
        # 存储会话状态
        self.sessions = {}

    @command("方舟猜猜乐")
    async def start_game(self, event: AstrMessageEvent): # 改为 AstrMessageEvent
        '''开始一局明日方舟干员猜猜乐'''
        session_id = event.get_session_id()
        
        if not self.operators:
            yield event.plain_result("❌ 插件数据文件丢失，无法开始游戏。")
            return

        target_name = random.choice(list(self.operators.keys()))
        
        self.sessions[session_id] = {
            "target": target_name,
            "history": [],
            "tries": 0
        }
        
        yield event.plain_result(f"🎮 游戏开始！我已经选好了一名干员。\n请直接发送干员名称进行猜测（共有 8 次机会）。")

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent): # 改为 AstrMessageEvent
        session_id = event.get_session_id()
        
        # 如果该会话没在游戏中，直接跳过
        if session_id not in self.sessions:
            return

        # 检查是否是纯文本消息
        user_input = event.get_plain_text().strip()
        
        # 如果输入的内容不是已知的干员，不触发逻辑（避免干扰正常聊天）
        if user_input not in self.operators:
            return 

        session = self.sessions[session_id]
        target_name = session["target"]
        
        # 1. 对比属性
        row_data = compare_attributes(user_input, target_name, self.operators)
        session["history"].append(row_data)
        session["tries"] += 1
        
        # 2. 生成反馈图
        img_name = f"temp_guess_{session_id}.png"
        img_path = os.path.join(os.path.dirname(__file__), img_name)
        
        try:
            render_table(session["history"], img_path)
            # 3. 发送图片反馈
            yield event.image_result(img_path)
        except Exception as e:
            # 这里的报错通常是因为缺少字体或 Pillow 没装
            yield event.plain_result(f"❌ 绘图出错，请检查服务器环境。")
            print(f"[Arknights Error] {e}")
            return
        
        # 4. 胜负判定
        if user_input == target_name:
            urls = self.operators[target_name].get("original_url", [])
            yield event.plain_result(f"🎉 恭喜！答案正是【{target_name}】！")
            if urls:
                yield event.image_result(random.choice(urls))
            
            del self.sessions[session_id]
            
        elif session["tries"] >= 8:
            yield event.plain_result(f"💀 机会用尽！正确答案是：{target_name}")
            urls = self.operators[target_name].get("original_url", [])
            if urls:
                yield event.image_result(random.choice(urls))
            
            del self.sessions[session_id]
