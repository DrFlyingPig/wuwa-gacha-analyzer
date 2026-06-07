"""
鸣潮抽卡分析器 - 后端服务
通过解析抽卡链接，调用鸣潮 API 获取抽卡记录并进行分析
"""

import time
import json
from urllib.parse import urlparse, parse_qs

import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 鸣潮抽卡记录 API
GACHA_API_URL = "https://gmserver-api.aki-game2.com/gacha/record/query"

# 卡池类型映射
POOL_TYPES = {
    1: {"name": "角色活动唤取", "short": "角色UP", "rarity_5": 0.008, "rarity_4": 0.06},
    2: {"name": "武器活动唤取", "short": "武器UP", "rarity_5": 0.008, "rarity_4": 0.06},
    3: {"name": "角色常驻唤取", "short": "常驻角色", "rarity_5": 0.006, "rarity_4": 0.06},
    4: {"name": "武器常驻唤取", "short": "常驻武器", "rarity_5": 0.006, "rarity_4": 0.06},
}

# 保底机制
PITY_LIMITS = {
    1: {"five_star": 80, "four_star": 10},  # 角色UP池
    2: {"five_star": 80, "four_star": 10},  # 武器UP池
    3: {"five_star": 80, "four_star": 10},  # 常驻角色池
    4: {"five_star": 80, "four_star": 10},  # 常驻武器池
}

# 常驻五星角色 resourceId（歪到这些角色 = 失败）
# 已确认的常驻角色：凌阳、卡卡罗、鉴心、维里奈、安可、相里要
STANDARD_5STAR_IDS = {
    1104,  # 凌阳
    1301,  # 卡卡罗
    1405,  # 鉴心
    # 以下 resourceId 基于游戏数据，如有误请修正
    1202,  # 维里奈
    1103,  # 安可
    1106,  # 相里要
}

# 角色头像映射 (中文名 -> 官网头像文件名)
# 来源: wutheringwaves.kurogames.com 官网 role-small 头像
CHAR_ICON_BASE = "https://wutheringwaves.kurogames.com/static4.0/assets/"
CHAR_ICON_MAP = {
    # 有 PNG 头像的角色
    "炽霞": "chixia-6dfd68f4.png",
    "秧秧": "yangyang-899b192b.png",
    "白芷": "baizhi-1e63bfde.png",
    "卡卡罗": "kakaluo-938f973c.png",
    "秋水": "qiushui-a6017d8a.png",
    "桃祈": "taoqi-4ecb9228.png",
    "丹瑾": "danjin-cc85e1c2.png",
    "莫特斐": "motefei-51fd5127.png",
    "凌阳": "lingyang-e6ad2f11.png",
    "渊武": "yuanwu-20ae8447.png",
    "鉴心": "jianxin-8c681929.png",
    "散华": "sanhua-db5af96c.png",
    "釉瑚": "youhu-b7a845b2.png",
    "灯灯": "dengdeng-100e326b.png",
    "维里奈": "weilinai-92d141b8.png",
    "安可": "anke-3bbb264c.png",
    "相里要": "xiangliyao-370c503c.png",
    # 只有 webp 头像的角色
    "达妮娅": "daniya-15bbe28e.webp",
    "卜灵": "buling-46d801eb.webp",
    "爱弥斯": "aimisi-c3b418c7.webp",
    "绯雪": "feixue-842a8cb5.webp",
    "夏空": "xiakong-a429a0dc.webp",
}


def get_char_icon(name):
    """获取角色头像 URL"""
    filename = CHAR_ICON_MAP.get(name)
    if not filename:
        return None
    return CHAR_ICON_BASE + filename


def parse_gacha_input(input_string):
    """
    解析抽卡链接/JSON，提取关键参数
    支持三种格式：
    1. JSON 请求体（如 {"playerId": "xxx", "serverId": "xxx", ...}）
    2. 完整 URL（如 https://xxx?playerId=xxx&serverId=xxx）
    3. 查询参数字符串（如 playerId=xxx&serverId=xxx）
    """
    input_string = input_string.strip()

    # 1. 尝试 JSON 格式解析
    if input_string.startswith("{"):
        try:
            params = json.loads(input_string)
            return {
                "serverId": params.get("serverId", ""),
                "playerId": params.get("playerId", ""),
                "roleId": params.get("roleId", ""),
                "languageCode": params.get("languageCode", "zh-Hans"),
                "recordId": params.get("recordId", ""),
            }
        except json.JSONDecodeError:
            pass

    # 2. URL 或查询参数格式
    if input_string.startswith("http"):
        parsed = urlparse(input_string)
        qs = parse_qs(parsed.query)
    else:
        if input_string.startswith("?"):
            input_string = input_string[1:]
        qs = parse_qs(input_string)

    def get_first(keys):
        for k in keys:
            if k in qs:
                return qs[k][0]
        return ""

    return {
        "serverId": get_first(["serverId", "svr_id"]),
        "playerId": get_first(["playerId", "player_id", "uid"]),
        "roleId": get_first(["roleId", "role_id"]),
        "languageCode": get_first(["languageCode", "langCode", "lang_code", "lang"]) or "zh-Hans",
        "recordId": get_first(["recordId", "record_id", "ticket"]),
    }


def fetch_gacha_records(server_id, player_id, role_id="", language_code="zh-Hans", record_id=""):
    """
    调用鸣潮 API 获取抽卡记录
    遍历所有卡池类型，获取全部记录
    """
    all_records = {}

    for pool_type in POOL_TYPES:
        payload = {
            "serverId": server_id,
            "playerId": player_id,
            "roleId": role_id or player_id,
            "languageCode": language_code,
            "cardPoolType": pool_type,
            "recordId": record_id,
        }

        try:
            print(f"请求卡池 {pool_type}，参数: {json.dumps(payload, ensure_ascii=False)}")
            resp = requests.post(GACHA_API_URL, json=payload, timeout=15)
            print(f"卡池 {pool_type} HTTP 状态码: {resp.status_code}")
            data = resp.json()
            print(f"卡池 {pool_type} 响应: {json.dumps(data, ensure_ascii=False)[:500]}")

            if data.get("code") != 200:
                print(f"卡池 {pool_type} API 返回错误: code={data.get('code')}, message={data.get('message')}")
                all_records[pool_type] = []
                continue

            # API 直接返回列表，不是 {"list": [...]}
            items = data.get("data", [])
            if not isinstance(items, list):
                items = []

            all_records[pool_type] = items
            print(f"卡池 {pool_type} ({POOL_TYPES[pool_type]['short']}): 获取 {len(items)} 条记录")

            time.sleep(0.2)

        except Exception as e:
            print(f"获取卡池 {pool_type} 记录失败: {e}")
            all_records[pool_type] = []

    return all_records


def analyze_pool(records, pool_type):
    """
    分析单个卡池的抽卡数据
    """
    empty_result = {
        "total_pulls": 0,
        "pity_5_count": 0,
        "pity_4_count": 0,
        "five_stars": [],
        "four_stars": [],
        "three_stars": 0,
        "avg_5star_pulls": 0,
        "luck_rating": "无数据",
        "win_count": 0,
        "lose_count": 0,
        "win_rate": 0,
    }

    if not records:
        return empty_result

    # 按时间排序（从旧到新）
    records.sort(key=lambda x: x.get("time", ""))

    total = len(records)
    five_stars = []
    four_stars = []
    three_stars = 0
    pity_5_counter = 0
    pity_4_counter = 0
    win_count = 0
    lose_count = 0

    for record in records:
        quality = record.get("qualityLevel", 0)
        pity_5_counter += 1
        pity_4_counter += 1

        if quality == 5:
            resource_id = record.get("resourceId", 0)
            resource_type = record.get("resourceType", "未知")
            name = record.get("name", "未知")
            is_standard = resource_id in STANDARD_5STAR_IDS

            # 仅在角色UP池判断歪没歪（只对角色类型生效）
            won_5050 = None
            if pool_type == 1 and resource_type == "角色":
                won_5050 = not is_standard
                if won_5050:
                    win_count += 1
                else:
                    lose_count += 1

            icon = get_char_icon(name) if resource_type == "角色" else None

            five_stars.append({
                "name": name,
                "type": resource_type,
                "time": record.get("time", ""),
                "pity_count": pity_5_counter,
                "is_early": pity_5_counter <= 50,
                "resource_id": resource_id,
                "won_5050": won_5050,
                "is_standard": is_standard,
                "icon": icon,
            })
            pity_5_counter = 0
            pity_4_counter = 0
        elif quality == 4:
            name = record.get("name", "未知")
            resource_type = record.get("resourceType", "未知")
            icon = get_char_icon(name) if resource_type == "角色" else None

            four_stars.append({
                "name": name,
                "type": resource_type,
                "time": record.get("time", ""),
                "pity_count": pity_4_counter,
                "icon": icon,
            })
            pity_4_counter = 0
        elif quality == 3:
            three_stars += 1

    # 计算统计指标
    avg_5star_pulls = 0
    if five_stars:
        pull_counts = [f["pity_count"] for f in five_stars]
        avg_5star_pulls = sum(pull_counts) / len(pull_counts)

    # 胜率计算
    total_5050 = win_count + lose_count
    win_rate = round(win_count / total_5050 * 100, 1) if total_5050 > 0 else 0

    # 欧非评价
    luck_rating = evaluate_luck(avg_5star_pulls, len(five_stars), total)

    return {
        "total_pulls": total,
        "pity_5_count": pity_5_counter,
        "pity_4_count": pity_4_counter,
        "five_stars": five_stars,
        "four_stars": four_stars,
        "three_stars": three_stars,
        "avg_5star_pulls": round(avg_5star_pulls, 1),
        "luck_rating": luck_rating,
        "win_count": win_count,
        "lose_count": lose_count,
        "win_rate": win_rate,
    }


def evaluate_luck(avg_pulls, five_star_count, total_pulls):
    """
    评价运气好坏
    """
    if five_star_count == 0:
        return "暂无五星"

    if avg_pulls <= 30:
        return "天选之人"
    elif avg_pulls <= 50:
        return "运气不错"
    elif avg_pulls <= 65:
        return "中规中矩"
    elif avg_pulls <= 75:
        return "有点非了"
    else:
        return "大非酋"


def get_summary(all_analysis):
    """
    生成总体摘要
    """
    total_pulls = 0
    total_five = 0
    total_four = 0
    all_five_star_pulls = []

    for pool_type, analysis in all_analysis.items():
        total_pulls += analysis["total_pulls"]
        total_five += len(analysis["five_stars"])
        total_four += len(analysis["four_stars"])
        for f in analysis["five_stars"]:
            all_five_star_pulls.append(f["pity_count"])

    avg_pulls = sum(all_five_star_pulls) / len(all_five_star_pulls) if all_five_star_pulls else 0

    return {
        "total_pulls": total_pulls,
        "total_five_stars": total_five,
        "total_four_stars": total_four,
        "avg_five_star_pulls": round(avg_pulls, 1),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    分析接口：接收抽卡链接/JSON，返回分析结果
    """
    data = request.get_json()
    url = data.get("url", "")

    if not url:
        return jsonify({"success": False, "error": "请输入抽卡链接或JSON"})

    # 解析输入
    params = parse_gacha_input(url)
    if not params.get("serverId") or not params.get("playerId"):
        return jsonify({"success": False, "error": "无法解析输入，请确认格式正确（支持JSON、URL、查询参数）。需要提供 serverId 和 playerId 参数。"})

    server_id = params["serverId"]
    player_id = params["playerId"]
    role_id = params.get("roleId", "")
    language_code = params.get("languageCode", "zh-Hans")
    record_id = params.get("recordId", "")

    # 获取抽卡记录
    try:
        all_records = fetch_gacha_records(server_id, player_id, role_id, language_code, record_id)
    except Exception as e:
        return jsonify({"success": False, "error": f"获取抽卡记录失败: {str(e)}"})

    # 分析各卡池
    all_analysis = {}
    for pool_type, records in all_records.items():
        pool_name = POOL_TYPES[pool_type]["short"]
        analysis = analyze_pool(records, pool_type)
        all_analysis[pool_name] = analysis

    # 生成摘要
    summary = get_summary(all_analysis)

    return jsonify({
        "success": True,
        "data": {
            "player_info": {
                "id": player_id,
                "server": server_id,
            },
            "pools": all_analysis,
            "summary": summary,
        }
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  鸣潮抽卡分析器")
    print("  访问 http://localhost:5000 开始使用")
    print("=" * 50)
    app.run(debug=True, port=5000)
