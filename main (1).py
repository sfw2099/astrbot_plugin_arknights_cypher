import os
import json
import random
import logging
import base64
import io
from astrbot.api.all import *
from .utils import compare_attributes, render_table

logger = logging.getLogger("astrbot")

@register("arknights_guess", "YourName", "明日方舟猜猜乐", "1.2.7")
class ArknightsGuessPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(self.plugin_dir, "arknights_fixed_positions.json")
        
        self.operators = {}
        self.high_star_names = [] # 新增：存放4-6星干员名字
        self.sessions = {}

        try:
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    self.operators = json.load(f)
                
                # 核心逻辑：筛选 4, 5, 6 星干员作为题库
                self.high_star_names = [
                    name for name, info in self.operators.items()
                    if info.get("星级") in ["4", "5", "6"]
                ]
                
                logger.info(f"明日方舟猜猜乐数据加载成功: 共 {len(self.operators)} 条，已锁定 {len(self.high_star_names)} 名高星干员作为题库。")
            else:
                logger.warning(f"未找到数据文件: {data_path}")
        except Exception as e:
            logger.error(f"加载数据异常: {e}")

    @command("猜干员")
    async def arknights_guess(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id in self.sessions:
            yield event.plain_result("游戏已经在进行中，请输入干员名字开始猜，或输入【结束方舟猜猜乐】。")
            return

        if not self.high_star_names:
            yield event.plain_result("干员数据未加载或星级筛选后为空，请检查数据文件。")
            return

        target_name = random.choice(self.high_star_names)
        
        self.sessions[session_id] = {
            "target": target_name,
            "history": [],
            "guessed_names": set(),  # 新增：记录已猜测的干员名，用于去重
            "tries": 0
        }
        
        yield event.plain_result("【明日方舟猜猜乐】开始！请输入干员名字开始猜测（最多8次机会）。")

    @command("结束猜干员")
    async def end_guess(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id in self.sessions:
            ans = self.sessions[session_id]["target"]
            yield event.plain_result(f"游戏已结束，正确答案是：{ans}")
            
            # 新增：手动结束也展示立绘
            urls = self.operators[ans].get("original_url", [])
            if urls:
                yield event.image_result(random.choice(urls))
                
            del self.sessions[session_id]

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id not in self.sessions:
            return
            
        user_input = event.message_str.strip()
        if user_input.startswith("/") or user_input in ["方舟猜猜乐", "结束方舟猜猜乐"]:
            return

        # 校验 1：干员是否存在
        if user_input not in self.operators:
            return 

        session = self.sessions[session_id]

        # 校验 2：是否重复猜测 (新增逻辑)
        if user_input in session["guessed_names"]:
            yield event.plain_result(f"干员【{user_input}】已经猜过啦，换一个试试吧！")
            return

        target_name = session["target"]

        # 1. 属性对比
        row_data = compare_attributes(user_input, target_name, self.operators)
        session["history"].append(row_data)
        session["guessed_names"].add(user_input) # 记录本次猜测
        session["tries"] += 1
        
        # 2. 渲染并发送结果图
        img_path = os.path.join(self.plugin_dir, f"temp_{session_id}.png")
        try:
            render_table(session["history"], img_path)
            # 直接传入本地文件路径字符串即可
            yield event.image_result(img_path)
        except Exception as e:
            logger.error(f"发送反馈图失败: {e}")
        
        # 3. 结局判定
        if user_input == target_name:
            yield event.plain_result(f"猜中了！答案是：【{target_name}】！")
            urls = self.operators[target_name].get("original_url", [])
            if urls: 
                yield event.image_result(random.choice(urls))
            if os.path.exists(img_path): 
                os.remove(img_path)
            del self.sessions[session_id]
        elif session["tries"] >= 8:
            yield event.plain_result(f"机会耗尽！答案是：【{target_name}】。")
            urls = self.operators[target_name].get("original_url", [])
            if urls: 
                yield event.image_result(random.choice(urls))
            if os.path.exists(img_path): 
                os.remove(img_path)
            del self.sessions[session_id]