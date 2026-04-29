"""
outreach.py - 多触点外展序列管理器。

管理线索通过3-4触点序列的流程：
  触点1（第0天）：LinkedIn连接请求（280字符）
  触点2（第3天）：跟进私信，包含具体发现
  触点3（第10天）：行业同行对比角度
  触点4（第21天）：告别消息

功能：
  - 每个线索的触点状态跟踪（内存中，可导出为JSON）
  - 每日限额控制（可配置，默认20个连接/天）
  - 今日待处理筛选（准备好下一个触点）
  - 序列导出，用于手动发送或CRM上传
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


DEFAULT_DAILY_LIMIT = int(os.environ.get("DEFAULT_DAILY_LIMIT", "20"))


class OutreachSequence:
    """
    管理一组线索的多触点外展序列。

    用法：
        seq = OutreachSequence(daily_limit=20)
        seq.add_leads(qualified_leads)
        due = seq.get_due_today()
        seq.mark_sent(domain, touch=1)
        seq.export("outreach-state.json")
    """

    TOUCH_GAPS = {
        1: 0,   # 第0天：连接请求
        2: 3,   # 触点1后第3天
        3: 7,   # 触点2后第7天（总计第10天）
        4: 11,  # 触点3后第11天（总计第21天）
    }

    def __init__(
        self,
        daily_limit: int = DEFAULT_DAILY_LIMIT,
        state: Optional[dict] = None,
    ):
        """
        Args:
            daily_limit: 每日最大连接请求数（仅触点1）
            state:       预加载的状态字典（来自导出/加载）
        """
        self.daily_limit = daily_limit
        # 状态：{domain: {touch, last_sent, scheduled_next, status, messages, ...}}
        self._state: dict[str, dict] = {}
        self._sends_today: dict[str, int] = {}  # date_str -> count

        if state:
            self._state = state.get("leads", {})
            self._sends_today = state.get("sends_today", {})

    def add_leads(self, leads: list[dict], force: bool = False) -> int:
        """
        将线索添加到序列中。

        Args:
            leads: 字典列表，每个包含domain + messages（来自message.py）
            force: 重新添加已跟踪的线索（重置其状态）

        Returns:
            新添加的线索数量
        """
        added = 0
        for lead in leads:
            domain = lead.get("domain", "")
            if not domain:
                continue
            if domain in self._state and not force:
                continue
            messages = lead.get("messages", {})
            self._state[domain] = {
                "domain": domain,
                "company": lead.get("company", domain),
                "contact_name": lead.get("contact_name", ""),
                "linkedin_url": lead.get("linkedin_url"),
                "touch": 0,          # 0 = 未开始
                "last_sent": None,
                "scheduled_next": datetime.now().strftime("%Y-%m-%d"),
                "status": "pending",  # pending / in_sequence / completed / skipped
                "connection_note": messages.get("connection_note", ""),
                "first_dm": messages.get("first_dm", ""),
                "followup_1": messages.get("followup", ""),
                "followup_2": messages.get("followup_2", ""),
                "followup_3": messages.get("followup_3", ""),
                "score": lead.get("qualification", {}).get("score") if "qualification" in lead else None,
                "tier": lead.get("qualification", {}).get("tier") if "qualification" in lead else None,
            }
            added += 1
        return added

    def get_due_today(
        self,
        touch: Optional[int] = None,
        include_overdue: bool = True,
    ) -> list[dict]:
        """
        返回今天待处理（或逾期）的线索。

        Args:
            touch:           筛选特定触点编号（1-4），或None表示全部
            include_overdue: 是否包含已过计划日期的线索

        Returns:
            线索状态字典列表，按分数降序排列（热门线索优先）
        """
        today = datetime.now().date()
        due = []

        for domain, s in self._state.items():
            if s["status"] in ("completed", "skipped"):
                continue

            current_touch = s["touch"]
            next_touch = current_touch + 1

            if next_touch > 4:
                if s["status"] != "completed":
                    s["status"] = "completed"
                continue

            if touch is not None and next_touch != touch:
                continue

            scheduled = s.get("scheduled_next")
            if not scheduled:
                continue

            try:
                scheduled_date = datetime.strptime(scheduled, "%Y-%m-%d").date()
            except ValueError:
                continue

            if scheduled_date <= today or (include_overdue and scheduled_date < today):
                due.append({**s, "next_touch": next_touch})

        def _sort_key(x):
            tier_order = {"hot": 0, "warm": 1, "cold": 2, None: 3}
            return (tier_order.get(x.get("tier"), 3), -(x.get("score") or 0))

        return sorted(due, key=_sort_key)

    def get_touch_message(self, domain: str, touch_number: int) -> str:
        """返回特定触点的消息文本。"""
        s = self._state.get(domain, {})
        mapping = {
            1: "connection_note",
            2: "first_dm",
            3: "followup_1",
            4: "followup_2",
        }
        key = mapping.get(touch_number, "")
        return s.get(key, "")

    def mark_sent(self, domain: str, touch: int) -> bool:
        """
        记录某个线索的触点已发送。

        Args:
            domain: 线索的域名
            touch:  已发送的触点编号（1-4）

        Returns:
            True表示已更新，False表示域名未找到
        """
        if domain not in self._state:
            return False

        s = self._state[domain]
        now_str = datetime.now().strftime("%Y-%m-%d")
        s["touch"] = touch
        s["last_sent"] = now_str
        s["status"] = "in_sequence"

        if touch == 1:
            self._sends_today[now_str] = self._sends_today.get(now_str, 0) + 1

        next_touch = touch + 1
        if next_touch > 4:
            s["status"] = "completed"
            s["scheduled_next"] = None
        else:
            gap = self.TOUCH_GAPS.get(next_touch, 7)
            next_date = datetime.now() + timedelta(days=gap)
            s["scheduled_next"] = next_date.strftime("%Y-%m-%d")

        return True

    def skip(self, domain: str, reason: str = "") -> bool:
        """将线索标记为跳过（从序列中移除）。"""
        if domain not in self._state:
            return False
        self._state[domain]["status"] = "skipped"
        if reason:
            self._state[domain]["skip_reason"] = reason
        return True

    def daily_capacity_remaining(self) -> int:
        """返回今天还可以发送多少个连接请求（触点1）。"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        sent_today = self._sends_today.get(today_str, 0)
        return max(0, self.daily_limit - sent_today)

    def get_stats(self) -> dict:
        """返回序列的汇总统计信息。"""
        counts = {"pending": 0, "in_sequence": 0, "completed": 0, "skipped": 0}
        touch_counts: dict[int, int] = {}
        tiers: dict[str, int] = {}

        for s in self._state.values():
            status = s.get("status", "pending")
            counts[status] = counts.get(status, 0) + 1
            touch = s.get("touch", 0)
            touch_counts[touch] = touch_counts.get(touch, 0) + 1
            tier = s.get("tier")
            if tier:
                tiers[tier] = tiers.get(tier, 0) + 1

        return {
            "total_leads": len(self._state),
            "status_breakdown": counts,
            "touch_breakdown": touch_counts,
            "tier_breakdown": tiers,
            "due_today": len(self.get_due_today()),
            "daily_capacity_remaining": self.daily_capacity_remaining(),
        }

    def export(self, path: Optional[str] = None) -> dict:
        """
        导出状态为JSON可序列化字典（可选写入文件）。

        Args:
            path: 写入的文件路径（可选）

        Returns:
            状态字典
        """
        data = {
            "exported_at": datetime.now().isoformat(),
            "daily_limit": self.daily_limit,
            "sends_today": self._sends_today,
            "leads": self._state,
        }
        if path:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        return data

    @classmethod
    def load(cls, path: str, daily_limit: Optional[int] = None) -> "OutreachSequence":
        """加载之前导出的状态文件。"""
        with open(path) as f:
            data = json.load(f)
        limit = daily_limit or data.get("daily_limit", DEFAULT_DAILY_LIMIT)
        return cls(daily_limit=limit, state=data)

    def print_queue(self, touch: Optional[int] = None) -> None:
        """将今日待处理队列打印到标准输出。"""
        due = self.get_due_today(touch=touch)
        if not due:
            print("[外展] 今天没有待处理的线索。", flush=True)
            return
        remaining = self.daily_capacity_remaining()
        tier_map = {"hot": "热门", "warm": "温暖", "cold": "冷淡"}
        print(
            f"[外展] {len(due)} 条线索今日待处理"
            f"（剩余 {remaining} 个连接名额）",
            flush=True,
        )
        for item in due:
            touch_num = item.get("next_touch", "?")
            tier = item.get("tier", "-")
            tier_cn = tier_map.get(tier, tier) if tier else "-"
            score = item.get("score", "-")
            msg_preview = self.get_touch_message(item["domain"], touch_num)[:60] if touch_num else ""
            print(
                f"  [{tier_cn}:{score}] "
                f"{item['company']}（{item['domain']}）"
                f"-> 触点{touch_num}：{msg_preview}...",
                flush=True,
            )
