from astrbot.api.all import *
from astrbot.api.event.filter import command
import json
from astrbot.api.message_components import At
import os
import logging
import random
from typing import Dict, List, Any

logger = logging.getLogger("MahjongPluginA")

# A规独立数据存储路径
DATA_DIR = os.path.join("data", "plugins", "astrbot_mahjong_a_plugin")
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "mahjong_data_a.json")

@register("N_league_A", "Vege", "日麻对局记录插件-A规", "1.0.0")
class MahjongPluginA(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data = self._load_data()
        self.active_matches = {}

    def _load_data(self) -> dict:
        if not os.path.exists(DATA_FILE):
            return {}
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载A规数据失败: {e}")
            return {}

    def _save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存A规数据失败: {e}")

    def _get_context_id(self, event: AstrMessageEvent) -> str:
        """获取上下文ID（群组ID或私聊ID）"""
        if hasattr(event, 'group_id') and event.group_id:
            return f"group_{event.group_id}"
        if hasattr(event, 'user_id') and event.user_id:
            return f"private_{event.user_id}"
        return "default_ctx"
        
    def _get_user_match(self, ctx_id: str, user_id: str):
        """查找指定用户当前所在的A规对局ID及对局数据"""
        if ctx_id not in self.active_matches:
            return None, None
        for mid, match in self.active_matches[ctx_id].items():
            if user_id in match["players"]:
                return mid, match
        return None, None

    @command("a_mj_start", alias=["a对局开始", "A对局开始", "a开房", "A开房"])
    async def start_match_a(self, event: AstrMessageEvent):
        """开始一场A规对局"""
        ctx_id = self._get_context_id(event)
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        
        mid, existing_match = self._get_user_match(ctx_id, user_id)
        if existing_match:
            yield event.plain_result(f"⚠️ 你已经在A规对局 #{mid} 中了，无法分身！")
            return

        if ctx_id not in self.active_matches:
            self.active_matches[ctx_id] = {}
            
        match_id = 1
        while str(match_id) in self.active_matches[ctx_id]:
            match_id += 1
        match_id = str(match_id)

        self.active_matches[ctx_id][match_id] = {
            "players": {user_id: user_name},
            "scores": {},
            "status": "recruiting"
        }
        
        yield event.plain_result(
            f"🅰️ A规对局 #{match_id} 已建立！\n"
            f"选手 {user_name} 已加入！ (1/4)\n"
            f"请其他选手发送 /a加入对局 加入。\n"
            f"(多桌同开时请输入 /a加入对局 {match_id} 加入本桌)"
        )

    @command("a_mj_join", alias=["a加入对局", "A加入对局", "a加入", "A加入"])
    async def join_match_a(self, event: AstrMessageEvent, match_id: str = ""):
        """加入当前招募中的A规对局"""
        ctx_id = self._get_context_id(event)
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        match_id = str(match_id).strip()

        mid, existing_match = self._get_user_match(ctx_id, user_id)
        if existing_match:
            yield event.plain_result(f"👉 {user_name} 已经在A规对局 #{mid} 中了。")
            return

        if ctx_id not in self.active_matches or not self.active_matches[ctx_id]:
            yield event.plain_result("⚠️ 当前没有正在招募的A规对局，请先发送 /a对局开始")
            return

        target_match, target_mid = None, None

        if match_id:
            if match_id in self.active_matches[ctx_id]:
                target_match = self.active_matches[ctx_id][match_id]
                target_mid = match_id
            else:
                yield event.plain_result(f"⚠️ 找不到A规对局 #{match_id}。")
                return
        else:
            recruiting_matches = {k: v for k, v in self.active_matches[ctx_id].items() if v["status"] == "recruiting"}
            if not recruiting_matches:
                yield event.plain_result("QAQ 当前所有的A规对局都已经人满开始了……")
                return
            elif len(recruiting_matches) == 1:
                target_mid, target_match = list(recruiting_matches.items())[0]
            else:
                match_list = ", ".join([f"#{k}" for k in recruiting_matches.keys()])
                yield event.plain_result(f"⚠️ 有多个正在招募的A规对局 ({match_list})，请指定桌号哦")
                return

        if target_match["status"] != "recruiting":
            yield event.plain_result(f"⚠️ A规对局 #{target_mid} 正在进行，无法加入。")
            return

        if len(target_match["players"]) >= 4:
            yield event.plain_result(f"🚫 A规对局 #{target_mid} 人数已满！")
            return

        target_match["players"][user_id] = user_name
        current_count = len(target_match["players"])

        if current_count == 4:
            target_match["status"] = "playing"
            
            # --- 自动分配东南西北风位 ---
            winds = ["东", "南", "西", "北"]
            player_list = list(target_match["players"].values())
            random.shuffle(player_list)
            players_list_str = "\n".join([f"{winds[i]}: {name}" for i, name in enumerate(player_list)])
            
            yield event.plain_result(
                f"✅ A规对局 #{target_mid} 集结完毕，GAME START！\n{players_list_str}\n\n"
                f"🏁 结束后请本桌选手发送：/a得点 [点数]"
            )
        else:
            yield event.plain_result(f"选手 {user_name} 加入A规对局 #{target_mid} ！ ({current_count}/4)")

    @command("a_mj_cancel", alias=["a取消对局", "A取消对局", "a解散", "A解散"])
    async def cancel_match_a(self, event: AstrMessageEvent):
        """解散用户当前所在的A规对局"""
        ctx_id = self._get_context_id(event)
        user_id = event.get_sender_id()

        mid, match = self._get_user_match(ctx_id, user_id)
        if match:
            status = match["status"]
            del self.active_matches[ctx_id][mid]
            if not self.active_matches[ctx_id]:
                del self.active_matches[ctx_id]
                
            if status == "recruiting":
                yield event.plain_result(f"🚫 已关闭A规对局招募 (桌号 #{mid})。")
            else:
                yield event.plain_result(f"🚫 已中止A规对局 #{mid}，本局数据不记录。")
        else:
            yield event.plain_result("⚠️ 你当前不在任何进行中的A规对局哦")

    @command("a_mj_end", alias=["a得点", "A得点", "a对局结束", "A对局结束"])
    async def end_match_a(self, event: AstrMessageEvent, score: int):
        """录入A规分数"""
        ctx_id = self._get_context_id(event)
        user_id = event.get_sender_id()
        
        mid, match = self._get_user_match(ctx_id, user_id)
        if not match:
            yield event.plain_result("⚠️ 你当前不在任何A规对局中")
            return

        if match["status"] != "playing":
            yield event.plain_result(f"⚠️ A规对局 #{mid} 尚未开始")
            return

        match["scores"][user_id] = score
        submitted_count = len(match["scores"])
        
        if submitted_count == 4:
            total_score = sum(match["scores"].values())
            
            # A规的供托不归还，因此只要合计点数不超过120000就算合法通过
            if total_score > 120000:
                diff = total_score - 120000
                details_str = "\n".join([f"{match['players'][uid]}: {s}" for uid, s in match["scores"].items()])
                
                yield event.plain_result(
                    f"⚠️ A规对局 #{mid} 点数核算不通过\n"
                    f"四家得点之和为 {total_score} (超出了12万分，误差 +{diff})\n"
                    f"目标: <= 120000\n"
                    f"----------------\n"
                    f"当前提交:\n{details_str}\n"
                    f"👉 请本桌发现错误的选手重新发送 /a得点 [正确点数] 修正。"
                )
                return 

            # 如果总和小于等于 120000，则直接进入结算
            yield event.plain_result(f"✅ A规对局 #{mid} 点数核算通过 (共 {total_score} 点)，正在结算...")
            
            for item in self._finalize_match_a(event, ctx_id, match, mid):
                yield item
        else:
            yield event.plain_result(f"💾 A规分数已记录 ({submitted_count}/4)")

    def _finalize_match_a(self, event, ctx_id, match, mid):
        """A规结算核心逻辑：水上动态马点 + 同分平分"""
        sorted_scores = sorted(match["scores"].items(), key=lambda x: x[1], reverse=True)
        ctx_data = self.data.setdefault(ctx_id, {})
        result_msg = [f"🅰️ A规对局结束"]
        
        # 计算水上人数 (>=30000)
        above_water = sum(1 for s in match["scores"].values() if s >= 30000)
        
        # A规顺位马点配置
        if above_water == 0:
            UMA_SLOTS = [0.0, 0.0, 0.0, 0.0]
        elif above_water == 1:
            UMA_SLOTS = [12.0, -1.0, -3.0, -8.0]
        elif above_water == 2:
            UMA_SLOTS = [8.0, 4.0, -4.0, -8.0]
        elif above_water == 3:
            UMA_SLOTS = [8.0, 3.0, 1.0, -12.0]
        else: # 4人水上 (理论不可能，除非有错和等特殊情况，这里兜个底)
            UMA_SLOTS = [0.0, 0.0, 0.0, 0.0]

        ICONS = ["🥇", "🥈", "🥉", "💀"]

        i = 0
        while i < len(sorted_scores):
            j = i + 1
            while j < len(sorted_scores) and sorted_scores[j][1] == sorted_scores[i][1]:
                j += 1
            
            # 同分平分马点
            current_umas = UMA_SLOTS[i:j]
            avg_uma = sum(current_umas) / len(current_umas)
            
            for k in range(i, j):
                uid, score = sorted_scores[k]
                username = match["players"][uid]
                
                # A规持点3w返点3w: (Score - 30000) / 1000 + 马点
                base_pt = (score - 30000) / 1000.0
                final_pt = round(base_pt + avg_uma, 1)
                pt_str = f"+{final_pt}" if final_pt > 0 else f"{final_pt}"
                
                user_stat = ctx_data.setdefault(uid, {
                    "name": username, "total_pt": 0.0, "total_matches": 0,
                    "ranks": [0, 0, 0, 0], "max_score": 0, "total_score": 0, "avoid_4_rate": 0.0
                })
                
                if "total_score" not in user_stat: user_stat["total_score"] = 0
                user_stat["name"] = username
                user_stat["total_pt"] = round(user_stat["total_pt"] + final_pt, 1)
                user_stat["total_matches"] += 1
                user_stat["ranks"][i] += 1
                user_stat["total_score"] += score
                
                if score > user_stat["max_score"]: user_stat["max_score"] = score
                not_4th_count = sum(user_stat["ranks"][:3])
                user_stat["avoid_4_rate"] = round((not_4th_count / user_stat["total_matches"]) * 100, 2)
                
                result_msg.append(f"{ICONS[i]} {username}: {score} ({pt_str}pt)")
            i = j
            
        self._save_data()

        del self.active_matches[ctx_id][mid]
        if not self.active_matches[ctx_id]:
            del self.active_matches[ctx_id]
        
        yield event.plain_result("\n".join(result_msg))

    @command("a_mj_chombo", alias=["a错和", "A错和", "a罚分", "a_chombo"])
    async def chombo_a(self, event: AstrMessageEvent):
        """
        A规错和处罚：扣除指定用户 20pt
        用法: /a错和 @用户 [备注]
        """
        ctx_id = self._get_context_id(event)
        
        target_uid = None
        for comp in event.get_messages():
            if isinstance(comp, At):
                target_uid = str(comp.qq)
                break
        
        if not target_uid:
            yield event.plain_result("⚠️ 格式错误，请 @ 需要处罚的用户。\n示例: /a错和 @某人 诈和")
            return

        reason_parts = []
        for comp in event.get_messages():
            if not isinstance(comp, At) and hasattr(comp, 'text'):
                reason_parts.append(comp.text)
                
        raw_text = " ".join(reason_parts).strip()
        for cmd in ["/a错和", "/A错和", "/a罚分", "/a_chombo"]:
            if raw_text.startswith(cmd):
                raw_text = raw_text[len(cmd):].strip()
                break
                
        reason = raw_text if raw_text else "无备注"

        ctx_data = self.data.setdefault(ctx_id, {})
        if target_uid not in ctx_data:
            ctx_data[target_uid] = {
                "name": f"用户{target_uid}", "total_pt": 0.0, "total_matches": 0,
                "ranks": [0, 0, 0, 0], "max_score": 0, "total_score": 0, "avoid_4_rate": 0.0
            }
        
        user_data = ctx_data[target_uid]
        user_data["total_pt"] = round(user_data["total_pt"] - 20.0, 1)
        self._save_data()
        
        yield event.plain_result(
            f"🚫 **A规 Chombo 处罚执行**\n"
            f"对象: {user_data['name']}\n"
            f"原因: {reason}\n"
            f"惩罚: -20 pt\n"
            f"当前 A规PT: {user_data['total_pt']}"
        )

    @command("a_mj_rank", alias=["a排行", "A排行", "a榜", "A榜"])
    async def show_rank_a(self, event: AstrMessageEvent):
        """
        A规排行榜：仅显示 PT 排行
        """
        ctx_id = self._get_context_id(event)
        ctx_data = self.data.get(ctx_id, {})
        
        if not ctx_data:
            yield event.plain_result("⚠️ 暂无A规对局记录。")
            return

        users = list(ctx_data.items())
        sorted_users = sorted(users, key=lambda x: x[1]["total_pt"], reverse=True)
            
        msg_lines = ["📊 **日常 A规 排行榜**"]
        for i, (uid, data) in enumerate(sorted_users):
            msg_lines.append(f"{i+1}. {data['name']} — {data['total_pt']} pt [试合:{data['total_matches']}]")

        yield event.plain_result("\n".join(msg_lines))

    @command("a_mj_stats", alias=["a吃鱼", "A吃鱼", "a个人数据", "a战绩"])
    async def my_stats_a(self, event: AstrMessageEvent):
        """
        A规个人数据查询
        """
        ctx_id = self._get_context_id(event)
        ctx_data = self.data.get(ctx_id, {})
        
        if not ctx_data:
            yield event.plain_result("⚠️ 暂无A规对局记录。")
            return

        target_uid = event.get_sender_id()
        target_name = event.get_sender_name()
        
        for comp in event.get_messages():
            if isinstance(comp, At):
                target_uid = str(comp.qq)
                if target_uid in ctx_data:
                    target_name = ctx_data[target_uid]["name"]
                else:
                    target_name = f"用户{target_uid}"
                break

        if target_uid not in ctx_data:
            yield event.plain_result(f"⚠️ 未找到 {target_name} 的 A规 参赛记录。")
            return

        user = ctx_data[target_uid]
        total_games = user["total_matches"]
        
        if total_games == 0:
            yield event.plain_result(f"⚠️ {user['name']} 还没有完成过A规对局。")
            return

        # 计算PT排名
        users_list = [{"uid": k, "total_pt": v["total_pt"]} for k, v in ctx_data.items()]
        users_list.sort(key=lambda x: x["total_pt"], reverse=True)
        try:
            pt_rank_idx = next(i for i, u in enumerate(users_list) if u["uid"] == target_uid)
            pt_rank = pt_rank_idx + 1
        except StopIteration:
            pt_rank = "N/A"
        
        ranks = user["ranks"]
        rates = [f"{r / total_games * 100:.2f}%" for r in ranks]
        rank_sum = sum((i + 1) * count for i, count in enumerate(ranks))
        avg_rank_val = rank_sum / total_games
        
        total_score = user.get("total_score", 0)
        avg_score = int(total_score / total_games)

        msg = [
            f"📊 **{user['name']} 的 A规 日常数据**",
            f"------------------------",
            f"🔢 • 当前PT: {user['total_pt']} pt (第 {pt_rank} 名)",
            f"",
            f"📈 ===对局详情=== (共 {total_games} 场)",
            f"🥇 一位率: {rates[0]} ({ranks[0]}回)",
            f"🥈 二位率: {rates[1]} ({ranks[1]}回)",
            f"🥉 三位率: {rates[2]} ({ranks[2]}回)",
            f"💀 四位率: {rates[3]} ({ranks[3]}回)",
            f"",
            f"📐 ===均值统计===",
            f"• 平均顺位: {avg_rank_val:.2f}",
            f"• 平均得点: {avg_score}",
            f"• 最高得点: {user['max_score']}",
            f"• 避四率: {user['avoid_4_rate']}%"
        ]
        
        yield event.plain_result("\n".join(msg))

    @command("a_mj_reset", alias=["a新赛季", "A新赛季", "a规重置"])
    async def reset_season_a(self, event: AstrMessageEvent):
        """重置A规的所有数据"""
        ctx_id = self._get_context_id(event)
        
        if ctx_id in self.active_matches:
            del self.active_matches[ctx_id]

        if ctx_id in self.data:
            self.data[ctx_id] = {} 
            self._save_data()
            yield event.plain_result("🔄 A规数据已完全重置！\n所有A规积分已清零。")
        else:
            yield event.plain_result("⚠️ 当前没有A规数据可重置。")
