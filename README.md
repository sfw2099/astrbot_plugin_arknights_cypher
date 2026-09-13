# 明日方舟干员猜猜挑战 (Arknights Cypher)

![Version](https://img.shields.io/badge/version-v1.6.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-AGPL--3.0-orange)

AstrBot 插件，模仿 PRTS Wiki 大帝的 Cypher 挑战 —— 通过属性对比猜测随机选定的明日方舟干员。

---

## 安装

### 方式一：AstrBot 插件市场
在 AstrBot WebUI 插件管理器中搜索 `arknights_cypher` 一键安装。

### 方式二：手动安装
```bash
git clone https://github.com/sfw2099/astrbot_plugin_arknights_cypher.git
```
将文件夹放入 AstrBot 的 `addons` 目录，重启 AstrBot 即可。

### 依赖
- **AstrBot** >= v4.23
- **Pillow** (PIL) — 用于渲染属性对比图
- **STZHONGS.TTF** — 华文中宋字体（已内置）

---

## 玩法

机器人随机选择一名 **4-6 星**干员作为答案，玩家通过输入干员名称进行猜测。每次猜测后会生成一张属性对比图，以图标方式展示各项属性的匹配情况：

| 图标 | 含义 |
|------|------|
|  | 属性完全一致 |
|  | 属性不同 |
|  | 星级偏低（目标更高星） |
|  | 星级偏高（目标更低星） |
|  | 数据未知 / 无法对比 |

最多 **8 次**猜测机会。

### 对比属性

| 维度 | 说明 |
|------|------|
| 干员名 | 本次猜测的干员 |
| 性别 | 男 / 女 / 未知 |
| 种族 | 如：菲林、萨卡兹、黎博利 |
| 星级 | 1-6 星 |
| 职业 | 近卫、术师、狙击等 |
| 分支 | 无畏者、扩散术师等 |
| 位置 | 近战位 / 远程位 / 兼有 |
| 势力 | 阵营 + 国家 + 组织集合对比（取交集判断） |

---

## 指令

| 指令 | 说明 |
|------|------|
| `猜干员` | 开始一局猜干员游戏 |
| `结束猜干员` | 提前结束当前游戏并揭示答案 |
| `检查干员更新` | 连接 PRTS Wiki 检查本地数据是否缺少新干员，自动拉取更新 |
| `随机干员 [星级]` | 随机抽取干员并返回随机立绘（可指定：`/随机干员 6` 或 `/随机干员 4 6`） |
| `干员信息 <干员名>` | 查询干员主要信息（星级/职业/分支/位置/性别/种族/势力/画师/标签）+ 一张立绘 |
| `干员屏蔽 <文字>` | 添加屏蔽词：抽干员时名字包含该文字的干员将被跳过（包含匹配，不区分大小写） |
| `干员屏蔽列表` | 查看当前屏蔽词列表 |
| `干员屏蔽移除 <文字>` | 移除指定屏蔽词 |
| `干员屏蔽清空` | 清空全部屏蔽词 |
| `干员星数` | 查看当前抽取星数范围 |
| `干员星数 <n>` | 设置仅抽取 n 星干员（如 `/干员星数 6`） |
| `干员星数 <a> <b>` | 设置抽取 a~b 星范围（如 `/干员星数 4 6`） |
| 直接发送干员名 | 进行猜测 |

> 屏蔽词与星数范围设置**持久保存**（重启后仍生效）。若屏蔽词覆盖了全部题库，当局自动忽略屏蔽并提示。屏蔽词上限 100 个。
>
> **星级说明**：v1.6.0 起星级为真实星级（1-6 星，六星=6）。旧数据（PRTS wikitext 0-indexed 格式）会在首次加载时自动迁移 +1。

---

## 数据来源

所有干员数据抓取自 [PRTS Wiki](https://prts.wiki/)（MediaWiki API），数据文件为 `arvetnights_fixed_positions.json`。

插件内置 `fetch_operators.py` 实用脚本，可独立运行以全量更新数据：

```bash
python fetch_operators.py
```

---

## 致谢

- 游戏灵感来源于 PRTS Wiki 的 [Cypher 小游戏](https://prts.wiki/)
- 数据接口由 PRTS Wiki MediaWiki API 提供

---

## License

GNU Affero General Public License v3.0
