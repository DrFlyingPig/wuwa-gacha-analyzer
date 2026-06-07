"""
鸣潮抽卡分析工具 - Flask 后端
"""

import json
import os
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 数据库路径
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "gacha.db")

# 鸣潮抽卡记录 API
GACHA_API_URL = "https://gmserver-api.aki-game2.com/gacha/record/query"

# 卡池类型映射
POOL_TYPES = {
    1: "角色UP池",
    2: "武器UP池",
    3: "常驻角色池",
    4: "常驻武器池",
}

# 大保底次数限制
PITY_LIMITS = {
    1: 80,  # 角色UP池
    2: 80,  # 武器UP池
    3: 80,  # 常驻角色池
    4: 80,  # 常驻武器池
}

# 常驻5星角色 ID
STANDARD_5STAR_IDS = {
    1104,  # 凌阳
    1301,  # 卡卡罗
    1405,  # 鉴心
    1202,  # 维里奈
    1103,  # 安可
    1106,  # 相里要
}

# 角色头像映射（官网 role-small 小头像）
CHAR_ICON_BASE = "https://wutheringwaves.kurogames.com/static4.0/assets/"
CHAR_ICON_MAP = {
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
    "达妮娅": "daniya-15bbe28e.webp",
    "卜灵": "buling-46d801eb.webp",
    "爱弥斯": "aimisi-c3b418c7.webp",
    "绯雪": "feixue-842a8cb5.webp",
    "夏空": "xiakong-a429a0dc.webp",
    # 默认头像（未知角色）
    "default": "default-6a0b12a0.png",
}


def get_db():
    """获取数据库连接"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gacha_records (
            id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            server_id TEXT,
            resource_id INTEGER,
            resource_name TEXT,
            resource_type TEXT,
            quality_level INTEGER,
            card_pool_type INTEGER,
            pull_time TEXT,
            count INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_pool
        ON gacha_records(player_id, card_pool_type)
    """)
    conn.commit()
    conn.close()


def save_records(player_id, server_id, records, pool_type):
    """保存抽卡记录，返回新增条数"""
    conn = get_db()
    new_count = 0
    # 用索引来确保唯一性
    for idx, r in enumerate(records):
        # 生成唯一 ID：playerId + pool_type + 索引 + time + resourceId
        record_id = f"{player_id}_{pool_type}_{idx}_{r.get('time', '')}_{r.get('resourceId', '')}"
        resource_name = r.get("resourceName") or r.get("name", "未知")
        cursor = conn.execute("""
            INSERT OR IGNORE INTO gacha_records
            (id, player_id, server_id, resource_id, resource_name,
             resource_type, quality_level, card_pool_type, pull_time, count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id, player_id, server_id,
            r.get("resourceId"), resource_name,
            r.get("resourceType"), r.get("qualityLevel"),
            pool_type, r.get("time"),
            r.get("count", 1)
        ))
        if cursor.rowcount > 0:
            new_count += 1
    conn.commit()
    conn.close()
    return new_count


def get_records(player_id, card_pool_type=None):
    """获取历史抽卡记录"""
    conn = get_db()
    if card_pool_type:
        rows = conn.execute("""
            SELECT * FROM gacha_records
            WHERE player_id = ? AND card_pool_type = ?
            ORDER BY pull_time DESC
        """, (player_id, card_pool_type)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM gacha_records
            WHERE player_id = ?
            ORDER BY pull_time DESC
        """, (player_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_record_count(player_id):
    """获取玩家的总记录数"""
    conn = get_db()
    result = conn.execute("""
        SELECT COUNT(*) as cnt FROM gacha_records WHERE player_id = ?
    """, (player_id,)).fetchone()
    conn.close()
    return result["cnt"]


# 启动时初始化数据库
init_db()


def parse_gacha_input(input_str):
    """解析用户输入的抽卡链接（JSON 格式）"""
    data = json.loads(input_str)
    result = {
        "player_id": data.get("playerId", ""),
        "server_id": data.get("serverId", ""),
        "language_code": data.get("languageCode", data.get("langCode", "zh-Hans")),
        "card_pool_id": data.get("cardPoolId", ""),
        "card_pool_type": data.get("cardPoolType", 1),
        "record_id": data.get("recordId", ""),
    }
    return result


def fetch_gacha_records(params):
    """从 API 获取抽卡记录"""
    payload = {
        "serverId": params["server_id"],
        "playerId": params["player_id"],
        "languageCode": params["language_code"],
        "cardPoolType": params["card_pool_type"],
        "cardPoolId": params["card_pool_id"],
        "recordId": params["record_id"],
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(GACHA_API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # 检查 API 返回状态
    code = data.get("code", -1)
    if code != 0:
        message = data.get("message", "未知错误")
        raise Exception(f"API 返回错误: {message} (code: {code})")

    return data.get("data", [])


def get_char_icon(name):
    """获取角色头像 URL"""
    filename = CHAR_ICON_MAP.get(name, CHAR_ICON_MAP.get("default", ""))
    return CHAR_ICON_BASE + filename


def analyze_pool(records, pool_type):
    """分析单个卡池的抽卡记录"""
    pool_name = POOL_TYPES.get(pool_type, "未知卡池")
    total = len(records)
    five_stars = []
    four_stars = []
    three_stars = []

    # API 返回的是时间倒序（最新在前），反转得到时间正序（最旧在前）
    # 不用 sorted() 以保持相同时间记录的原始顺序
    records_sorted = list(reversed(records))

    # 记录上一个5星的位置
    last_five_idx = -1

    for idx, r in enumerate(records_sorted):
        quality = r.get("qualityLevel", 3)
        resource_name = r.get("resourceName") or r.get("name", "未知")
        item = {
            "name": resource_name,
            "quality": quality,
            "time": r.get("time", ""),
            "type": r.get("resourceType", ""),
            "id": r.get("resourceId"),
        }

        # 添加头像
        if item["type"] == "角色":
            item["icon"] = get_char_icon(item["name"])
        else:
            item["icon"] = ""

        if quality == 5:
            # 计算距上一个5星的抽数
            pulls_since_last = idx - last_five_idx
            item["pull_number"] = pulls_since_last
            last_five_idx = idx

            # 判断是否歪了（仅限角色UP池）
            if pool_type == 1:
                item["is_standard"] = item["id"] in STANDARD_5STAR_IDS
                item["won_5050"] = not item["is_standard"]
            five_stars.append(item)
        elif quality == 4:
            # 4星也显示距上一个5星的抽数
            item["pull_number"] = idx - last_five_idx
            if item["type"] == "角色":
                item["icon"] = get_char_icon(item["name"])
            four_stars.append(item)
        else:
            three_stars.append(item)

    # 计算当前保底进度（最后一个5星之后的抽数）
    pity_count = total - 1 - last_five_idx if last_five_idx >= 0 else total

    # 50/50 统计（仅角色UP池）
    win_count = 0
    lose_count = 0
    win_rate = "N/A"
    if pool_type == 1 and five_stars:
        win_count = sum(1 for f in five_stars if f.get("won_5050"))
        lose_count = sum(1 for f in five_stars if f.get("is_standard"))
        if win_count + lose_count > 0:
            win_rate = f"{win_count / (win_count + lose_count) * 100:.1f}%"

    return {
        "pool_name": pool_name,
        "pool_type": pool_type,
        "total": total,
        "five_stars": five_stars,
        "four_stars": four_stars,
        "three_stars": three_stars,
        "pity_count": pity_count,
        "pity_limit": PITY_LIMITS.get(pool_type, 80),
        "win_count": win_count,
        "lose_count": lose_count,
        "win_rate": win_rate,
    }


def evaluate_luck(pity_count, pity_limit, total, five_count):
    """评估运气"""
    if five_count == 0:
        return "暂无5星记录"

    avg_pulls = total / five_count if five_count > 0 else 0

    if avg_pulls <= 30:
        return "🌟 超级欧皇！"
    elif avg_pulls <= 50:
        return "🍀 运气不错"
    elif avg_pulls <= 65:
        return "😐 运气一般"
    elif avg_pulls <= 75:
        return "😰 有点非了"
    else:
        return "💀 非酋附体"


def get_summary(results):
    """生成总结"""
    total_all = sum(r["total"] for r in results)
    total_five = sum(len(r["five_stars"]) for r in results)
    total_four = sum(len(r["four_stars"]) for r in results)

    summary_lines = []
    summary_lines.append(f"共抽取 **{total_all}** 次")
    summary_lines.append(f"获得 5星 **{total_five}** 个，4星 **{total_four}** 个")
    summary_lines.append("")

    for r in results:
        if r["total"] > 0:
            line = f"**{r['pool_name']}**：{r['total']}抽，5星{len(r['five_stars'])}个"
            if r["pool_type"] == 1 and r["win_rate"] != "N/A":
                line += f"，胜率{r['win_rate']}"
            summary_lines.append(line)

    return "\n".join(summary_lines)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    try:
        data = request.get_json()
        input_str = data.get("input", "")

        if not input_str:
            return jsonify({"success": False, "error": "请输入抽卡链接"}), 400

        params = parse_gacha_input(input_str)
        player_id = params["player_id"]
        server_id = params["server_id"]

        # 从 API 获取所有卡池的记录
        all_records = {}
        api_errors = []
        for pool_type in POOL_TYPES:
            params_copy = params.copy()
            params_copy["card_pool_type"] = pool_type
            try:
                records = fetch_gacha_records(params_copy)
                if records:
                    # 保存到数据库，传入整数类型的 pool_type
                    save_records(player_id, server_id, records, pool_type)
                    all_records[pool_type] = records
            except Exception as e:
                error_msg = str(e)
                print(f"获取卡池 {pool_type} 失败: {error_msg}")
                api_errors.append(error_msg)

        # 如果所有卡池都获取失败，返回错误信息
        if not all_records and api_errors:
            # 检查是否是 recordId 过期
            if any("code: -1" in err for err in api_errors):
                return jsonify({
                    "success": False,
                    "error": "recordId 已过期，请重新打开游戏抽卡历史页面，抓包获取新的请求数据"
                }), 400
            else:
                return jsonify({
                    "success": False,
                    "error": f"获取抽卡记录失败: {api_errors[0]}"
                }), 500

        # 从数据库读取完整记录进行分析
        results = []
        for pool_type in POOL_TYPES:
            # 从数据库获取该卡池的所有记录
            db_records = get_records(player_id, pool_type)
            if not db_records:
                continue

            # 转换为分析格式
            formatted_records = []
            for r in db_records:
                formatted_records.append({
                    "resourceId": r["resource_id"],
                    "resourceName": r["resource_name"],
                    "name": r["resource_name"],
                    "resourceType": r["resource_type"],
                    "qualityLevel": r["quality_level"],
                    "cardPoolType": r["card_pool_type"],
                    "time": r["pull_time"],
                    "count": r["count"],
                })

            result = analyze_pool(formatted_records, pool_type)
            result["luck"] = evaluate_luck(
                result["pity_count"],
                result["pity_limit"],
                result["total"],
                len(result["five_stars"])
            )
            results.append(result)

        # 如果没有结果，可能是 recordId 过期且数据库为空
        if not results:
            return jsonify({
                "success": False,
                "error": "没有找到抽卡记录。如果是第一次使用，请确保 recordId 有效；如果是之前已保存过记录，请检查 playerId 是否正确"
            }), 400

        summary = get_summary(results)
        total_records = get_record_count(player_id)

        return jsonify({
            "success": True,
            "results": results,
            "summary": summary,
            "player_id": player_id,
            "total_records": total_records,
        })
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "JSON 格式错误，请检查输入"}), 400
    except requests.RequestException as e:
        return jsonify({"success": False, "error": f"网络请求失败: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"分析失败: {str(e)}"}), 500


@app.route("/api/history", methods=["GET"])
def api_history():
    """查询历史记录"""
    try:
        player_id = request.args.get("player_id", "")
        if not player_id:
            return jsonify({"success": False, "error": "缺少 player_id"}), 400

        # 获取所有记录
        records = get_records(player_id)

        # 按卡池分组
        grouped = {}
        for r in records:
            pool_type = r["card_pool_type"]
            if pool_type not in grouped:
                grouped[pool_type] = []
            grouped[pool_type].append({
                "resourceId": r["resource_id"],
                "resourceName": r["resource_name"],
                "name": r["resource_name"],
                "resourceType": r["resource_type"],
                "qualityLevel": r["quality_level"],
                "cardPoolType": r["card_pool_type"],
                "time": r["pull_time"],
                "count": r["count"],
            })

        # 分析每个卡池
        results = []
        for pool_type in sorted(grouped.keys()):
            result = analyze_pool(grouped[pool_type], pool_type)
            result["luck"] = evaluate_luck(
                result["pity_count"],
                result["pity_limit"],
                result["total"],
                len(result["five_stars"])
            )
            results.append(result)

        summary = get_summary(results)
        total_records = len(records)

        return jsonify({
            "success": True,
            "results": results,
            "summary": summary,
            "player_id": player_id,
            "total_records": total_records,
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"查询失败: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
