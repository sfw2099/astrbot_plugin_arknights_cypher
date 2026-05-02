import os
import requests
import re
import json

API_URL = "https://prts.wiki/api.php"
DATA_FILE = "arknights_fixed_positions.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_all_operator_names():
    names = []
    cmcontinue = ""
    while True:
        params = {
            "action": "query", "format": "json", "list": "categorymembers",
            "cmtitle": "Category:干员", "cmlimit": "max", "cmcontinue": cmcontinue
        }
        try:
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10).json()
            members = resp.get("query", {}).get("categorymembers", [])
            for m in members:
                name = m['title']
                if not any(k in name for k in ["分类:", "列表", "索引", "Template:"]):
                    names.append(name)
            cmcontinue = resp.get("continue", {}).get("cmcontinue")
            if not cmcontinue: break
        except:
            break
    return list(set(names))

def get_all_skin_urls(name):
    original_urls = []
    thumbnail_url = ""
    search_name = name.replace(" ", "_")
    params = {
        "action": "query",
        "format": "json",
        "list": "allimages",
        "aiprefix": f"立绘_{search_name}",
        "ailimit": "30"
    }
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10).json()
        images = resp.get("query", {}).get("allimages", [])
        images.sort(key=lambda x: x.get("name", ""))
        for img in images:
            img_name = img.get("name", "")
            if img_name.startswith(f"立绘_{search_name}_") or img_name == f"立绘_{search_name}.png":
                url = img.get("url")
                original_urls.append(url)
                if not thumbnail_url:
                    thumbnail_url = img.get("url")
    except:
        pass
    return original_urls, thumbnail_url

def fetch_operator_detail(name):
    params = {
        "action": "parse",
        "page": name,
        "format": "json",
        "prop": "wikitext",
        "redirects": 1
    }
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10).json()
        if "error" in resp: return None
        wikitext = resp["parse"]["wikitext"]["*"]

        def extract(pattern, default="未知"):
            match = re.search(pattern, wikitext)
            return match.group(1).strip() if match else default

        prof = extract(r"\|职业=([^|\n]+)")
        sub_prof = extract(r"\|分支=([^|\n]+)")
        rarity = extract(r"\|稀有度=([1-6])", "0")
        gender = extract(r"\|性别=([^|\n]+)")
        race = extract(r"\|种族=([^|\n]+)")
        nation = extract(r"\|所属国家=([^|\n]+)")
        team = extract(r"\|所属团队=([^|\n]+)")
        group = extract(r"\|所属组织=([^|\n]+)")
        raw_tags = extract(r"\|标签=([^|\n]+)", "")
        raw_pos = extract(r"\|位置=([^|\n]+)")
        painter = extract(r"\|画师=([^|\n]+)")

        if sub_prof in ["推击手", "钩索师"]:
            position = "近战/远程兼具 (地面/高台均可)"
        else:
            position = "近战位" if "近战" in raw_pos else "远程位" if "远程" in raw_pos else raw_pos

        images, thumb = get_all_skin_urls(name)

        return {
            "original_url": images,
            "thumbnail_url": thumb,
            "星级": rarity,
            "职业分支": f"{prof} - {sub_prof}",
            "性别": gender,
            "阵营": nation if nation != "未知" else team,
            "获取途径": [],
            "标签": [t for t in raw_tags.split(' ') if t],
            "初始生命": "-", "初始攻击": "-", "初始防御": "-", "初始法抗": "-",
            "再部署": "-", "部署费用": "-", "阻挡数": "-", "攻击间隔": "-",
            "是否感染": "未知",
            "职业": prof,
            "分支": sub_prof,
            "画师": painter,
            "种族": race,
            "位置": position,
            "国家": nation,
            "组织": group
        }
    except:
        return None

def check_missing_operators(plugin_dir):
    data_path = os.path.join(plugin_dir, DATA_FILE)
    wiki_names = get_all_operator_names()
    if not wiki_names:
        return None, 0, 0
    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            current = json.load(f)
    else:
        current = {}
    existing = set(current.keys())
    missing = [n for n in wiki_names if n not in existing]
    return missing, len(wiki_names), len(existing)

def update_missing_operators(plugin_dir, missing_names):
    data_path = os.path.join(plugin_dir, DATA_FILE)
    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}
    results = {"added": [], "failed": []}
    for i, name in enumerate(missing_names):
        detail = fetch_operator_detail(name)
        if detail:
            data[name] = detail
            results["added"].append(name)
        else:
            results["failed"].append(name)
        if (i + 1) % 10 == 0:
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return results

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    names = get_all_operator_names()
    if not names:
        print("未能获取名单，请检查网络。")
        return
    full_data = {}
    total = len(names)
    print(f"开始同步 {total} 名干员数据...")
    for i, name in enumerate(names):
        detail = fetch_operator_detail(name)
        if detail:
            full_data[name] = detail
            img_count = len(detail['original_url'])
            print(f"[{i+1}/{total}] {name} - 完成 (立绘数: {img_count})")
        if (i + 1) % 20 == 0:
            path = os.path.join(script_dir, DATA_FILE)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(full_data, f, ensure_ascii=False, indent=2)
    path = os.path.join(script_dir, DATA_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    print(f"\n同步完成！数据保存至: {path}")

if __name__ == "__main__":
    main()
