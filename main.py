import os
import json
import random
import re
import logging
import asyncio
from astrbot.api.all import *
from .utils import compare_attributes, render_table
from .fetch_operators import check_missing_operators, update_missing_operators

logger = logging.getLogger("astrbot")

@register("arknights_guess", "YourName", "明日方舟猜猜乐", "1.5.0")
class ArknightsGuessPlugin(Star):
    BLOCK_FILE = "blocked_keywords.json"
    STAR_FILE = "star_range.json"
    MAX_BLOCKED = 100

    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(self.plugin_dir, "arknights_fixed_positions.json")

        self.operators = {}
        self.high_star_names = [] # 题库（按星数范围筛选）
        self.sessions = {}
        self.blocked_keywords = []   # 屏蔽词列表（包含匹配）
        self.star_min, self.star_max = 4, 6  # 抽取星数范围（真实星级 1-6）

        try:
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    self.operators = json.load(f)
                self._migrate_star_ratings(data_path)
                self._rebuild_pool()
                logger.info(f"明日方舟猜猜乐数据加载成功: 共 {len(self.operators)} 条，题库 {len(self.high_star_names)} 名（{self.star_min}~{self.star_max} 星）。")
            else:
                logger.warning(f"未找到数据文件: {data_path}")
        except Exception as e:
            logger.error(f"加载数据异常: {e}")

        self._load_block_keywords()
        self._load_star_range()
        self._rebuild_pool()

    def _migrate_star_ratings(self, data_path):
        """星级偏移迁移：PRTS wikitext 稀有度为 0-indexed（0-5 = 实际 1-6 星）。

        旧数据特征：存在星级为 '0' 的条目（Robot 干员，真实体系无 0 星）。
        检测到则全体 +1 并写回（一次性，幂等）。
        """
        has_zero = any(str(info.get("星级")) == "0" for info in self.operators.values())
        if not has_zero:
            return
        for info in self.operators.values():
            raw = info.get("星级")
            if str(raw).isdigit():
                info["星级"] = str(int(raw) + 1)
        try:
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(self.operators, f, ensure_ascii=False, indent=2)
            logger.info("星级数据已迁移为真实星级（+1，旧格式 0-5 → 1-6）。")
        except Exception as e:
            logger.error(f"星级迁移写回失败: {e}")

    # ==================== 屏蔽词与星数范围存储 ====================

    def _load_block_keywords(self):
        path = os.path.join(self.plugin_dir, self.BLOCK_FILE)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.blocked_keywords = [str(x) for x in data if str(x).strip()]
        except Exception as e:
            logger.error(f"加载屏蔽词失败: {e}")

    def _save_block_keywords(self):
        path = os.path.join(self.plugin_dir, self.BLOCK_FILE)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.blocked_keywords, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存屏蔽词失败: {e}")

    def _load_star_range(self):
        path = os.path.join(self.plugin_dir, self.STAR_FILE)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                lo, hi = int(data.get("min", 4)), int(data.get("max", 6))
                if 1 <= lo <= hi <= 6:
                    self.star_min, self.star_max = lo, hi
        except Exception as e:
            logger.error(f"加载星数范围失败: {e}")

    def _save_star_range(self):
        path = os.path.join(self.plugin_dir, self.STAR_FILE)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"min": self.star_min, "max": self.star_max}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存星数范围失败: {e}")

    def _rebuild_pool(self):
        """按当前星数范围重建题库。"""
        self.high_star_names = [
            name for name, info in self.operators.items()
            if str(info.get("星级", "")).isdigit() and self.star_min <= int(info.get("星级")) <= self.star_max
        ]

    def _pick_target(self):
        """从题库中按屏蔽词过滤后随机抽取。返回 (target_name, 警告消息或None)。"""
        blocked = [kw for kw in self.blocked_keywords if kw.strip()]
        pool = [n for n in self.high_star_names
                if not any(kw.lower() in n.lower() for kw in blocked)]
        if not pool:
            return random.choice(self.high_star_names), "⚠️ 屏蔽词覆盖了全部题库，本局忽略屏蔽规则。"
        return random.choice(pool), None

    # ==================== 屏蔽词指令 ====================

    @command("干员屏蔽")
    async def block_operator(self, event: AstrMessageEvent):
        raw = str(event.message_str or "").strip()
        keyword = re.sub(r"^[/／]?\s*干员屏蔽\s*", "", raw).strip()
        if not keyword:
            yield event.plain_result("用法：/干员屏蔽 <文字>——抽干员时名字包含该文字的干员将被跳过。\n相关：/干员屏蔽列表 /干员屏蔽移除 <文字> /干员屏蔽清空")
            return
        if len(self.blocked_keywords) >= self.MAX_BLOCKED:
            yield event.plain_result(f"屏蔽词已达上限（{self.MAX_BLOCKED} 个），请先清理：/干员屏蔽列表")
            return
        if any(kw.lower() == keyword.lower() for kw in self.blocked_keywords):
            yield event.plain_result(f"屏蔽词「{keyword}」已存在。")
            return
        self.blocked_keywords.append(keyword)
        self._save_block_keywords()
        pool_cnt = len([n for n in self.high_star_names
                        if not any(kw.lower() in n.lower() for kw in self.blocked_keywords)])
        yield event.plain_result(f"🚫 已添加屏蔽词「{keyword}」（当前 {len(self.blocked_keywords)} 个，剩余可抽干员 {pool_cnt} 名）。")

    @command("干员屏蔽列表")
    async def list_blocked(self, event: AstrMessageEvent):
        if not self.blocked_keywords:
            yield event.plain_result("当前没有屏蔽词。用法：/干员屏蔽 <文字>")
            return
        lines = [f"🚫 屏蔽词列表（{len(self.blocked_keywords)} 个，包含匹配）："]
        lines.extend(f"  {i+1}. {kw}" for i, kw in enumerate(self.blocked_keywords))
        yield event.plain_result("\n".join(lines))

    @command("干员屏蔽移除")
    async def unblock_operator(self, event: AstrMessageEvent):
        raw = str(event.message_str or "").strip()
        keyword = re.sub(r"^[/／]?\s*干员屏蔽移除\s*", "", raw).strip()
        if not keyword:
            yield event.plain_result("用法：/干员屏蔽移除 <文字>")
            return
        before = len(self.blocked_keywords)
        self.blocked_keywords = [kw for kw in self.blocked_keywords if kw.lower() != keyword.lower()]
        if len(self.blocked_keywords) == before:
            yield event.plain_result(f"未找到屏蔽词「{keyword}」。")
            return
        self._save_block_keywords()
        yield event.plain_result(f"✅ 已移除屏蔽词「{keyword}」（剩余 {len(self.blocked_keywords)} 个）。")

    @command("干员屏蔽清空")
    async def clear_blocked(self, event: AstrMessageEvent):
        n = len(self.blocked_keywords)
        self.blocked_keywords = []
        self._save_block_keywords()
        yield event.plain_result(f"🧹 已清空全部屏蔽词（原 {n} 个）。")

    # ==================== 星数范围指令 ====================

    @command("干员星数")
    async def set_star_range(self, event: AstrMessageEvent):
        raw = str(event.message_str or "").strip()
        arg = re.sub(r"^[/／]?\s*干员星数\s*", "", raw).strip()
        if not arg:
            pool_cnt = len(self.high_star_names)
            yield event.plain_result(
                f"⭐ 当前抽取星数范围：{self.star_min}~{self.star_max} 星（题库 {pool_cnt} 名）\n"
                "用法：/干员星数 6（仅六星）｜ /干员星数 4 6（四到六星）"
            )
            return
        parts = arg.replace("～", " ").replace("-", " ").split()
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            yield event.plain_result("用法：/干员星数 6 ｜ /干员星数 4 6（星数 1~6）")
            return
        if len(nums) == 1:
            lo = hi = nums[0]
        elif len(nums) == 2:
            lo, hi = min(nums), max(nums)
        else:
            yield event.plain_result("用法：/干员星数 6 ｜ /干员星数 4 6")
            return
        if not (1 <= lo <= hi <= 6):
            yield event.plain_result("星数范围需在 1~6 之间且起点不大于终点。")
            return
        self.star_min, self.star_max = lo, hi
        self._save_star_range()
        self._rebuild_pool()
        yield event.plain_result(
            f"⭐ 已设置抽取星数范围：{lo}~{hi} 星（题库 {len(self.high_star_names)} 名）。"
        )

    @command("随机干员")
    async def random_operator(self, event: AstrMessageEvent):
        """随机抽取干员并返回随机立绘：/随机干员 [星级]，如 /随机干员 6 或 /随机干员 4 6"""
        if not self.operators:
            yield event.plain_result("干员数据未加载，请先发送 /检查干员更新。")
            return
        raw = str(event.message_str or "").strip()
        arg = re.sub(r"^[/／]?\s*随机干员\s*", "", raw).strip()
        pool = list(self.operators.keys())
        if arg:
            parts = arg.replace("～", " ").replace("-", " ").split()
            try:
                nums = [int(p) for p in parts]
            except ValueError:
                yield event.plain_result("用法：/随机干员 ｜ /随机干员 6 ｜ /随机干员 4 6")
                return
            if len(nums) == 1:
                lo = hi = nums[0]
            elif len(nums) == 2:
                lo, hi = min(nums), max(nums)
            else:
                yield event.plain_result("用法：/随机干员 ｜ /随机干员 6 ｜ /随机干员 4 6")
                return
            if not (1 <= lo <= hi <= 6):
                yield event.plain_result("星数范围需在 1~6 之间。")
                return
            pool = [n for n, info in self.operators.items()
                    if str(info.get("星级", "")).isdigit() and lo <= int(info.get("星级")) <= hi]
            if not pool:
                yield event.plain_result(f"该星数范围（{lo}~{hi} 星）没有干员数据。")
                return
        name = random.choice(pool)
        urls = self.operators[name].get("original_url", [])
        star = self.operators[name].get("星级", "?")
        yield event.plain_result(f"🎲 随机干员：【{name}】（{star} 星）")
        if urls:
            yield event.image_result(random.choice(urls))
        else:
            yield event.plain_result("（该干员暂无立绘数据）")

    @command("干员信息")
    async def operator_info(self, event: AstrMessageEvent):
        """查询干员主要信息并展示一张立绘：/干员信息 <干员名>"""
        if not self.operators:
            yield event.plain_result("干员数据未加载，请先发送 /检查干员更新。")
            return
        raw = str(event.message_str or "").strip()
        name = re.sub(r"^[/／]?\s*干员信息\s*", "", raw).strip()
        if not name:
            yield event.plain_result("用法：/干员信息 <干员名>（如：/干员信息 维什戴尔）")
            return
        # 精确匹配优先，其次包含匹配（唯一时直接用）
        if name in self.operators:
            target = name
        else:
            matches = [n for n in self.operators if name in n]
            if len(matches) == 1:
                target = matches[0]
            elif len(matches) > 1:
                preview = "、".join(matches[:8]) + ("…" if len(matches) > 8 else "")
                yield event.plain_result(f"找到 {len(matches)} 名包含「{name}」的干员：{preview}\n请输入完整名称。")
                return
            else:
                yield event.plain_result(f"未找到干员「{name}」。请确认名称（可用 /检查干员更新 同步数据）。")
                return
        info = self.operators[target]
        lines = [
            f"📋 【{target}】",
            f"⭐ 星级：{info.get('星级', '未知')}",
            f"⚔️ 职业：{info.get('职业', '未知')} - {info.get('分支', '未知')}",
            f"📍 位置：{info.get('位置', '未知')}",
            f"👤 性别：{info.get('性别', '未知')}｜ 种族：{info.get('种族', '未知')}",
            f"🏛️ 势力：{info.get('阵营', '未知')}",
            f"🎨 画师：{info.get('画师', '未知')}",
        ]
        tags = info.get("标签") or []
        if tags:
            lines.append(f"🏷️ 标签：{'、'.join(str(t) for t in tags)}")
        yield event.plain_result("\n".join(lines))
        urls = info.get("original_url", [])
        if urls:
            yield event.image_result(random.choice(urls))
        else:
            yield event.plain_result("（该干员暂无立绘数据）")

    @command("猜干员")
    async def arknights_guess(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id in self.sessions:
            yield event.plain_result("游戏已经在进行中，请输入干员名字开始猜，或输入【结束方舟猜猜乐】。")
            return

        if not self.high_star_names:
            yield event.plain_result("干员数据未加载或星级筛选后为空，请检查数据文件。")
            return

        target_name, warn = self._pick_target()
        
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

    @command("检查干员更新")
    async def check_operator_updates(self, event: AstrMessageEvent):
        yield event.plain_result("正在连接 PRTS Wiki 检查干员更新，请稍候...")

        try:
            loop = asyncio.get_event_loop()
            missing, wiki_count, current_count = await loop.run_in_executor(
                None, check_missing_operators, self.plugin_dir
            )
        except Exception as e:
            logger.error(f"检查干员更新失败: {e}")
            yield event.plain_result("检查失败，无法连接到 PRTS Wiki，请稍后重试。")
            return

        if missing is None:
            yield event.plain_result("检查失败，无法连接到 PRTS Wiki，请稍后重试。")
            return

        if not missing:
            yield event.plain_result(
                f"数据已是最新！当前共 {current_count} 名干员，Wiki 共 {wiki_count} 名。"
            )
            return

        missing_list = "\n".join(f"  {i+1}. {n}" for i, n in enumerate(missing[:15]))
        truncate = f"\n  ... 等共 {len(missing)} 名" if len(missing) > 15 else ""
        yield event.plain_result(
            f"发现 {len(missing)} 名新干员 "
            f"(Wiki: {wiki_count} → 本地: {current_count})：\n"
            f"{missing_list}{truncate}\n\n正在自动拉取数据，请稍候..."
        )

        try:
            result = await loop.run_in_executor(
                None, update_missing_operators, self.plugin_dir, missing
            )
        except Exception as e:
            logger.error(f"更新干员数据失败: {e}")
            yield event.plain_result(f"数据拉取失败: {e}")
            return

        data_path = os.path.join(self.plugin_dir, "arknights_fixed_positions.json")
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                self.operators = json.load(f)
            self._migrate_star_ratings(data_path)
            self._rebuild_pool()
        except Exception as e:
            logger.error(f"重新加载数据失败: {e}")

        yield event.plain_result(
            f"更新完成！成功添加 {len(result['added'])} 名干员，"
            f"失败 {len(result['failed'])} 名。\n"
            f"当前共 {len(self.operators)} 名干员 "
            f"(高星题库 {len(self.high_star_names)} 名)。"
        )

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