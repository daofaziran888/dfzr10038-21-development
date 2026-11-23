"""逐行拒绝归因领域服务。

覆盖整条闭环：
1. 从接入任务检索实际触发的字段与检查项，归因上带规则修订号；
2. 同一源键跨两种原因只计一行（按字段筛选、翻页都按源键去重口径）；
3. 质量工作台逐项待办（一个检查项一条，而非整行复查），认领并提交更正；
4. 规则修订发布后旧修订留档、最高生效修订成为现用规则；
5. 接入入口重送：仅当现用规则逐项都有通过依据时才接收，否则当次拒收；
6. 指定规则修订号的回测；口径调整后重算旧批对照，原批映射与拒绝依据仍可查。
"""
from __future__ import annotations

import datetime
from typing import Any

from app.store import store


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _next_id(table: str) -> int:
    return max((int(row.get("id", 0)) for row in store.rows(table)), default=0) + 1


def _paginate(rows: list[dict[str, Any]], page: int, size: int) -> tuple[list[dict[str, Any]], int]:
    total = len(rows)
    start = (page - 1) * size
    return rows[start:start + size], total


class RejectionService:
    """逐行拒绝归因 + 质量工作台 + 重送闭环的领域服务。"""

    # ---- 通用规则与口径 -------------------------------------------------

    def current_revision(self, rule_no: str) -> dict[str, Any] | None:
        """现用规则：同规则编号下「生效中」且修订号最大的一版。"""
        candidates = [
            row for row in store.rows("qc_rule_revision")
            if row.get("规则编号") == rule_no and row.get("status") == "生效中"
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda row: int(row.get("修订号", 0)))

    def rule_at_revision(self, rule_no: str, revision_no: int) -> dict[str, Any] | None:
        for row in store.rows("qc_rule_revision"):
            if row.get("规则编号") == rule_no and int(row.get("修订号", 0)) == revision_no:
                return row
        return None

    def list_rule_revisions(self, rule_no: str | None = None) -> list[dict[str, Any]]:
        rows = store.rows("qc_rule_revision")
        if rule_no:
            rows = [row for row in rows if row.get("规则编号") == rule_no]
        return sorted(rows, key=lambda row: (str(row.get("规则编号")), int(row.get("修订号", 0))))

    # ---- 检查引擎：在给定规则修订上判定单个值 -----------------------------

    @staticmethod
    def _is_blank(value: Any) -> bool:
        return value is None or str(value).strip() == "" or str(value).strip().upper() in {"NULL", "NONE"}

    def evaluate(self, rule: dict[str, Any], raw_value: Any, converted_value: Any) -> bool:
        """按指定修订的规则内容判定是否通过。返回 True 表示通过。"""
        check_type = str(rule.get("检查类型", ""))
        revision_no = int(rule.get("修订号", 1))
        if check_type == "格式校验":
            value = str(converted_value if not self._is_blank(converted_value) else raw_value or "")
            token = str(value).strip()
            return token.isdigit() and 10 <= len(token) <= 19
        if check_type == "空值校验":
            # 修订号 1：转换后为空即拒绝；修订号 2 起：仅原始值缺失才拒绝。
            if revision_no <= 1:
                return not self._is_blank(converted_value)
            return not self._is_blank(raw_value)
        return True

    # ---- 1. 逐行拒绝归因查询（源键去重口径） ------------------------------

    def list_attributions(
        self,
        *,
        batch_no: str | None = None,
        source_key: str | None = None,
        field: str | None = None,
        check_item: str | None = None,
        rule_no: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        """返回按源键聚合的归因视图。

        每个源键一条聚合行，内含命中的若干检查项；源键跨两种原因只计一行，
        因此字段筛选/翻页的 total 是去重后的源键数，与实际拒绝量口径一致。
        """
        attrs = store.rows("qc_reject_attr")
        if batch_no:
            attrs = [row for row in attrs if row.get("批次编号") == batch_no]
        if source_key:
            attrs = [row for row in attrs if source_key.casefold() in str(row.get("源键", "")).casefold()]
        if field:
            attrs = [row for row in attrs if field.casefold() in str(row.get("字段", "")).casefold()]
        if check_item:
            attrs = [row for row in attrs if check_item.casefold() in str(row.get("检查项", "")).casefold()]
        if rule_no:
            attrs = [row for row in attrs if rule_no.casefold() in str(row.get("规则编号", "")).casefold()]

        # 按源键聚合，保持首次出现顺序。
        grouped: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for attr in attrs:
            key = str(attr.get("源键", ""))
            if key not in grouped:
                grouped[key] = {
                    "批次编号": attr.get("批次编号"),
                    "源键": key,
                    "行号": attr.get("行号"),
                    "字段": attr.get("字段"),
                    "命中检查项": [],
                    "命中规则修订": [],
                    "拒绝原因数": 0,
                }
                order.append(key)
            grouped[key]["命中检查项"].append(str(attr.get("检查项", "")))
            grouped[key]["命中规则修订"].append(
                f"{attr.get('规则编号')}#{attr.get('规则修订号')}"
            )
        for key in order:
            grouped[key]["拒绝原因数"] = len(grouped[key]["命中检查项"])

        # 源键去重后的实际拒绝量口径。
        distinct_source_keys = order
        items = [grouped[key] for key in distinct_source_keys]
        page_items, total = _paginate(items, page, size)
        summary = {
            "distinct_rejected_rows": len(distinct_source_keys),
            "attribution_records": len(attrs),
            "caliber": "源键去重：同一源键命中多项检查只计一行",
        }
        return page_items, total, summary

    def attribution_detail(self, batch_no: str, source_key: str) -> dict[str, Any]:
        """单个源键的完整档案：源行、逐项归因（带修订号）、待办与结论、重送历史。"""
        source_row = next(
            (row for row in store.rows("qc_source_row")
             if row.get("批次编号") == batch_no and row.get("源键") == source_key),
            None,
        )
        attrs = [
            row for row in store.rows("qc_reject_attr")
            if row.get("批次编号") == batch_no and row.get("源键") == source_key
        ]
        todos = [
            row for row in store.rows("qc_review_todo")
            if row.get("批次编号") == batch_no and row.get("源键") == source_key
        ]
        conclusions = [
            row for row in store.rows("qc_review_conclusion")
            if row.get("批次编号") == batch_no and row.get("源键") == source_key
        ]
        resends = [
            row for row in store.rows("qc_resend_record")
            if row.get("批次编号") == batch_no and row.get("源键") == source_key
        ]
        return {
            "批次编号": batch_no,
            "源键": source_key,
            "源行": source_row,
            "归因明细": attrs,
            "待办": todos,
            "复查结论": conclusions,
            "重送记录": resends,
        }

    # ---- 2. 质量工作台逐项待办 -------------------------------------------

    def list_todos(
        self,
        *,
        batch_no: str | None = None,
        source_key: str | None = None,
        check_item: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows("qc_review_todo")
        if batch_no:
            rows = [row for row in rows if row.get("批次编号") == batch_no]
        if source_key:
            rows = [row for row in rows if source_key.casefold() in str(row.get("源键", "")).casefold()]
        if check_item:
            rows = [row for row in rows if check_item.casefold() in str(row.get("检查项", "")).casefold()]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if assignee:
            rows = [row for row in rows if assignee.casefold() in str(row.get("认领人", "")).casefold()]
        return _paginate(rows, page, size)

    def claim_todo(self, todo_id: int, assignee: str) -> tuple[dict[str, Any] | None, str]:
        todo = self._find("qc_review_todo", todo_id)
        if todo is None:
            return None, f"待办 {todo_id} 不存在"
        if todo.get("status") != "待认领":
            return None, f"待办 {todo_id} 当前状态为{todo.get('status')}，不能重复认领"
        if not assignee.strip():
            return None, "认领时必须填写认领人"
        todo["status"] = "已认领"
        todo["认领人"] = assignee.strip()
        todo["认领时间"] = _now()
        todo["pending"] = True
        return todo, f"质量员{assignee}已认领逐项待办（{todo.get('检查项')}）"

    def submit_correction(
        self, todo_id: int, *, corrected_raw: str, corrected_converted: str, remark: str = ""
    ) -> tuple[dict[str, Any] | None, str]:
        """提交逐项更正：只覆盖该待办对应的单个检查项，不强制整行复查。"""
        todo = self._find("qc_review_todo", todo_id)
        if todo is None:
            return None, f"待办 {todo_id} 不存在"
        if todo.get("status") != "已认领":
            return None, f"待办 {todo_id} 尚未认领，不能提交更正"

        rule_no = str(todo.get("规则编号"))
        current = self.current_revision(rule_no)
        # 现用规则较归因时已改版 → 不能沿用旧结论，需按现用修订重跑该检查项。
        recheck = current is not None and int(current.get("修订号", 0)) > int(
            todo.get("归因规则修订号", 0)
        )
        applied_rule = current if recheck else self.rule_at_revision(
            rule_no, int(todo.get("归因规则修订号", 1))
        )
        passed = self.evaluate(applied_rule, corrected_raw, corrected_converted)

        conclusion = {
            "id": _next_id("qc_review_conclusion"),
            "status": "复查通过" if passed else "复查不通过",
            "pending": not passed,
            "abnormal": not passed,
            "批次编号": todo.get("批次编号"),
            "源键": todo.get("源键"),
            "字段": todo.get("字段"),
            "检查项": todo.get("检查项"),
            "规则编号": rule_no,
            "归因规则修订号": todo.get("归因规则修订号"),
            "执行规则修订号": applied_rule.get("修订号"),
            "复查模式": "按现用修订重跑" if recheck else "沿用仍有效的逐项结论",
            "更正原始值": corrected_raw,
            "更正转换值": corrected_converted,
            "检查结果": "通过" if passed else "不通过",
            "复查人": todo.get("认领人"),
            "备注": remark,
            "复查时间": _now(),
        }
        store.rows("qc_review_conclusion").append(conclusion)

        todo["status"] = "更正已提交"
        todo["pending"] = False
        todo["更正原始值"] = corrected_raw
        todo["更正转换值"] = corrected_converted
        todo["执行规则修订号"] = applied_rule.get("修订号")
        todo["复查模式"] = conclusion["复查模式"]
        return conclusion, (
            f"逐项更正已提交，按 {rule_no}#{applied_rule.get('修订号')} "
            f"{'重跑' if recheck else '沿用有效结论'}，检查结果：{conclusion['检查结果']}"
        )

    # ---- 3. 规则修订发布（原转换/校验规则可改版，旧版留档） -----------------

    def publish_revision(
        self, rule_no: str, *, rule_content: str, check_type: str | None = None
    ) -> tuple[dict[str, Any] | None, str]:
        existing = [row for row in store.rows("qc_rule_revision") if row.get("规则编号") == rule_no]
        if not existing:
            return None, f"规则 {rule_no} 不存在，无法发布修订"
        next_rev = max(int(row.get("修订号", 0)) for row in existing) + 1
        base = existing[0]
        for row in existing:
            if row.get("status") == "生效中":
                row["status"] = "已改版"
                row["是否现用"] = False
                row["pending"] = False
        revision = {
            "id": _next_id("qc_rule_revision"),
            "status": "生效中",
            "pending": True,
            "abnormal": False,
            "规则编号": rule_no,
            "检查项": base.get("检查项"),
            "检查字段": base.get("检查字段"),
            "修订号": next_rev,
            "是否现用": True,
            "检查类型": check_type or base.get("检查类型"),
            "规则内容": rule_content,
            "阻断级别": base.get("阻断级别"),
            "生效时间": _now(),
        }
        store.rows("qc_rule_revision").append(revision)
        # 规则改版后，针对该规则已提交的逐项待办按旧修订的结论失效，
        # 自动退回待认领，使质量员能在新修订上重跑该检查项（不影响其他检查项待办）。
        reopened = 0
        for todo in store.rows("qc_review_todo"):
            if todo.get("规则编号") != rule_no:
                continue
            if todo.get("status") in {"更正已提交", "已认领"}:
                todo["status"] = "待认领"
                todo["pending"] = True
                todo["abnormal"] = True
                todo["认领人"] = ""
                todo.pop("认领时间", None)
                todo.pop("更正原始值", None)
                todo.pop("更正转换值", None)
                todo.pop("执行规则修订号", None)
                todo["待重跑原因"] = f"规则已改版至 #{next_rev}，旧修订结论失效"
                reopened += 1
        return revision, (
            f"规则 {rule_no} 已发布修订 #{next_rev}，旧修订留档可查；"
            f"{reopened} 条逐项待办退回待认领以按新修订重跑"
        )

    # ---- 4. 接入入口重送：现用规则逐项都有通过依据才接收 -------------------

    def resend(
        self, batch_no: str, source_key: str, *, operator: str = "接入入口"
    ) -> tuple[dict[str, Any] | None, str]:
        source_row = next(
            (row for row in store.rows("qc_source_row")
             if row.get("批次编号") == batch_no and row.get("源键") == source_key),
            None,
        )
        if source_row is None:
            return None, f"批次 {batch_no} 中找不到源键 {source_key}"

        # 该源键归因命中的全部规则（去重），逐项核对现用修订。
        rule_nos = sorted({
            str(attr.get("规则编号"))
            for attr in store.rows("qc_reject_attr")
            if attr.get("批次编号") == batch_no and attr.get("源键") == source_key
        })
        checks: list[dict[str, Any]] = []
        all_pass = True
        for rule_no in rule_nos:
            current = self.current_revision(rule_no)
            # 取该源键针对该规则最新的一条复查结论作为通过依据。
            conclusions = [
                row for row in store.rows("qc_review_conclusion")
                if row.get("批次编号") == batch_no
                and row.get("源键") == source_key
                and row.get("规则编号") == rule_no
            ]
            latest = conclusions[-1] if conclusions else None
            has_valid_pass = bool(
                latest
                and latest.get("检查结果") == "通过"
                and int(latest.get("执行规则修订号", 0)) == int(current.get("修订号", 0))
            )
            # 重送时用最新更正值（若有）在现用规则上复算，作为接入端独立判定。
            raw_value = latest.get("更正原始值") if latest else source_row.get("原始值")
            converted_value = (
                latest.get("更正转换值") if latest else source_row.get("转换值")
            )
            engine_pass = self.evaluate(current, raw_value, converted_value)
            passed = has_valid_pass and engine_pass
            all_pass = all_pass and passed
            checks.append({
                "规则编号": rule_no,
                "检查项": current.get("检查项"),
                "现用修订号": current.get("修订号"),
                "通过依据": "逐项复查结论且与现用修订一致" if has_valid_pass else "缺少现用修订的通过结论",
                "接入端复算": "通过" if engine_pass else "不通过",
                "接收判定": "通过" if passed else "拒收",
            })

        accepted = all_pass
        record = {
            "id": _next_id("qc_resend_record"),
            "status": "已接收" if accepted else "拒收",
            "pending": not accepted,
            "abnormal": not accepted,
            "批次编号": batch_no,
            "源键": source_key,
            "操作人": operator,
            "重送时间": _now(),
            "逐项判定": checks,
            "拒收原因": "" if accepted else "仍有现用规则缺少通过依据或复算不通过",
        }
        store.rows("qc_resend_record").append(record)
        if accepted:
            source_row["当前接收状态"] = "已接收"
            source_row["status"] = "已接收"
            source_row["pending"] = False
            source_row["abnormal"] = False
        message = (
            f"源键 {source_key} 重送{'成功，已接收' if accepted else '被拒收'}："
            + "；".join(f"{c['检查项']}={c['接收判定']}" for c in checks)
        )
        return record, message

    # ---- 5. 指定规则修订号回测 -------------------------------------------

    def backtest(self, rule_no: str, revision_no: int, *, batch_no: str | None = None) -> tuple[dict[str, Any] | None, str]:
        rule = self.rule_at_revision(rule_no, revision_no)
        if rule is None:
            return None, f"规则 {rule_no} 修订 #{revision_no} 不存在"
        rows = store.rows("qc_source_row")
        if batch_no:
            rows = [row for row in rows if row.get("批次编号") == batch_no]
        details = []
        hit = 0
        for row in rows:
            passed = self.evaluate(rule, row.get("原始值"), row.get("转换值"))
            if not passed:
                hit += 1
            details.append({
                "批次编号": row.get("批次编号"),
                "源键": row.get("源键"),
                "回测结果": "通过" if passed else "拒绝",
            })
        result = {
            "id": _next_id("qc_rule_backtest"),
            "status": "已出分",
            "pending": False,
            "abnormal": hit > 0,
            "规则编号": rule_no,
            "回测修订号": revision_no,
            "回测批次": batch_no or "全部批次",
            "样本行数": len(rows),
            "拒绝行数": hit,
            "通过行数": len(rows) - hit,
            "逐行结果": details,
            "回测时间": _now(),
        }
        store.rows("qc_rule_backtest").append(result)
        return result, f"回测完成：{rule_no}#{revision_no} 样本 {len(rows)} 行，拒绝 {hit} 行"

    def list_backtests(self, rule_no: str | None = None) -> list[dict[str, Any]]:
        rows = store.rows("qc_rule_backtest")
        if rule_no:
            rows = [row for row in rows if row.get("规则编号") == rule_no]
        return rows

    # ---- 6. 口径调整后重算旧批对照（原批留档，只追加） ---------------------

    def recompute_batch(self, batch_no: str) -> tuple[dict[str, Any] | None, str]:
        batch = next((row for row in store.rows("qc_batch") if row.get("批次编号") == batch_no), None)
        if batch is None:
            return None, f"批次 {batch_no} 不存在"
        source_rows = [row for row in store.rows("qc_source_row") if row.get("批次编号") == batch_no]
        rule_nos = sorted({
            str(attr.get("规则编号"))
            for attr in store.rows("qc_reject_attr")
            if attr.get("批次编号") == batch_no
        })
        per_row = []
        new_distinct = 0
        for row in source_rows:
            failed_items = []
            for rule_no in rule_nos:
                current = self.current_revision(rule_no)
                if not self.evaluate(current, row.get("原始值"), row.get("转换值")):
                    failed_items.append(f"{rule_no}#{current.get('修订号')}")
            if failed_items:
                new_distinct += 1
            per_row.append({
                "源键": row.get("源键"),
                "现口径拒绝项": failed_items,
                "现口径判定": "拒绝" if failed_items else "通过",
            })
        result = {
            "id": _next_id("qc_batch_recompute"),
            "status": "已重算",
            "pending": False,
            "abnormal": False,
            "批次编号": batch_no,
            "原口径版本": batch.get("校验口径版本"),
            "原拒绝行数": batch.get("拒绝行数"),
            "现口径拒绝行数": new_distinct,
            "原字段映射": batch.get("字段映射"),
            "原拒绝依据可查": True,
            "逐行对照": per_row,
            "重算时间": _now(),
        }
        store.rows("qc_batch_recompute").append(result)
        return result, (
            f"批次 {batch_no} 已按现口径重算对照：原拒绝 {batch.get('拒绝行数')} 行 → "
            f"现口径拒绝 {new_distinct} 行；原批字段映射与拒绝依据保留可查"
        )

    def list_recomputes(self, batch_no: str | None = None) -> list[dict[str, Any]]:
        rows = store.rows("qc_batch_recompute")
        if batch_no:
            rows = [row for row in rows if row.get("批次编号") == batch_no]
        return rows

    # ---- 辅助 ------------------------------------------------------------

    @staticmethod
    def _find(table: str, entry_id: int) -> dict[str, Any] | None:
        for row in store.rows(table):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def list_batches(self) -> list[dict[str, Any]]:
        return store.rows("qc_batch")

    def list_source_rows(self, batch_no: str | None = None) -> list[dict[str, Any]]:
        rows = store.rows("qc_source_row")
        if batch_no:
            rows = [row for row in rows if row.get("批次编号") == batch_no]
        return rows

    def snapshot(self) -> dict[str, Any]:
        return {
            "规则修订数": len(store.rows("qc_rule_revision")),
            "归因记录数": len(store.rows("qc_reject_attr")),
            "待办数": len(store.rows("qc_review_todo")),
            "待认领待办": sum(1 for row in store.rows("qc_review_todo") if row.get("status") == "待认领"),
            "复查结论数": len(store.rows("qc_review_conclusion")),
            "重送记录数": len(store.rows("qc_resend_record")),
            "回测次数": len(store.rows("qc_rule_backtest")),
            "重算次数": len(store.rows("qc_batch_recompute")),
        }


rejection_service = RejectionService()
