"""逐行拒绝归因子域的示例数据。

接入任务只给拒绝总量，本模块补齐「按源行追查被拒原始行」的入口：
- qc_rule_revision   质量检查规则修订（同一检查项多修订号，最高生效修订为现用规则）
- qc_batch           接入批次（冻结当时口径：字段映射、规则修订、统计口径）
- qc_source_row      批次内源行（源键、原始值、转换值）
- qc_reject_attr     逐行拒绝归因（源键 × 字段 × 检查项 × 规则修订号）
- qc_review_todo     质量工作台逐检查项待办（逐项，而非整行）
- qc_review_conclusion 复查/更正结论（记录依据的规则修订号）
- qc_resend_record   接入入口重送记录（按本轮覆盖检查决定是否接收）
- qc_rule_backtest   指定规则修订号的回测结果
- qc_batch_recompute 口径调整后旧批对照重算结果（原批留档，只追加对照）

只依赖标准库，服务启动即可演示完整故事：A 同时命中账户格式与空值，B 只命中旧格式。
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 质量检查规则修订
# ---------------------------------------------------------------------------

QC_RULE_REVISION_SEED: list[dict[str, Any]] = [
    {
        "id": 1,
        "status": "生效中",
        "pending": True,
        "abnormal": False,
        "规则编号": "QUAL-ACCT-FMT",
        "检查项": "账户号格式",
        "检查字段": "账户号",
        "修订号": 1,
        "是否现用": True,
        "检查类型": "格式校验",
        "规则内容": "账户号须为 10-19 位数字（原始账户号格式，纯数字才放行）",
        "阻断级别": "阻断",
        "生效时间": "2026-10-01T09:00:00",
    },
    {
        "id": 2,
        "status": "生效中",
        "pending": True,
        "abnormal": False,
        "规则编号": "QUAL-ACCT-NULL",
        "检查项": "账户号空值",
        "检查字段": "账户号",
        "修订号": 1,
        "是否现用": True,
        "检查类型": "空值校验",
        "规则内容": "转换后的账户号为空即拒绝（空白、NULL、NONE 均视为空）",
        "阻断级别": "阻断",
        "生效时间": "2026-10-01T09:00:00",
    },
]

# 空值校验改版后的修订在运行期由「发布修订」动作按上一版结构自动生成，
# 因此这里只维护初始基线，不预置模板。

# ---------------------------------------------------------------------------
# 接入批次（按当时口径留档）
# ---------------------------------------------------------------------------

QC_BATCH_SEED: list[dict[str, Any]] = [
    {
        "id": 1,
        "status": "部分拒绝",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "接入任务编号": "BATC-0002",
        "数据源": "crm_account_daily",
        "目标特征": "user_account_no",
        "字段映射": "src.account_no -> user_account_no（trim 后存储）",
        "口径修订基线": "QUAL-ACCT-FMT#1;QUAL-ACCT-NULL#1",
        "校验口径版本": 1,
        "接入行数": 2,
        "拒绝行数": 2,
        "接入时间": "2026-11-10T08:30:00",
    },
]

# ---------------------------------------------------------------------------
# 批次内源行
# ---------------------------------------------------------------------------

QC_SOURCE_ROW_SEED: list[dict[str, Any]] = [
    {
        "id": 1,
        "status": "已拒绝",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-A",
        "行号": 17,
        "字段": "账户号",
        "原始值": "ACCT-9031 ",
        "转换值": "",
        "转换规则修订": "TRIM-RULE#1",
        "当前接收状态": "拒收",
    },
    {
        "id": 2,
        "status": "已拒绝",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-B",
        "行号": 23,
        "字段": "账户号",
        "原始值": "9032-OLD",
        "转换值": "9032-OLD",
        "转换规则修订": "TRIM-RULE#1",
        "当前接收状态": "拒收",
    },
]

# ---------------------------------------------------------------------------
# 逐行拒绝归因（同一源键可跨两种原因，源键去重后只计一行）
# ---------------------------------------------------------------------------

QC_REJECT_ATTR_SEED: list[dict[str, Any]] = [
    {
        "id": 1,
        "status": "待复查",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-A",
        "行号": 17,
        "字段": "账户号",
        "检查项": "账户号格式",
        "规则编号": "QUAL-ACCT-FMT",
        "规则修订号": 1,
        "拒绝依据": "原始值 ACCT-9031 含字母与连字符，不满足 10-19 位数字格式",
        "触发阶段": "原始值校验",
        "归因时间": "2026-11-10T08:30:01",
    },
    {
        "id": 2,
        "status": "待复查",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-A",
        "行号": 17,
        "字段": "账户号",
        "检查项": "账户号空值",
        "规则编号": "QUAL-ACCT-NULL",
        "规则修订号": 1,
        "拒绝依据": "转换后账户号为空字符串，命中空值阻断",
        "触发阶段": "转换值校验",
        "归因时间": "2026-11-10T08:30:01",
    },
    {
        "id": 3,
        "status": "待复查",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-B",
        "行号": 23,
        "字段": "账户号",
        "检查项": "账户号格式",
        "规则编号": "QUAL-ACCT-FMT",
        "规则修订号": 1,
        "拒绝依据": "原始值 9032-OLD 含连字符与字母，不满足 10-19 位数字格式",
        "触发阶段": "原始值校验",
        "归因时间": "2026-11-10T08:30:01",
    },
]

# ---------------------------------------------------------------------------
# 质量工作台逐项待办（每个归因检查项一条；不是整行复查）
# ---------------------------------------------------------------------------

QC_REVIEW_TODO_SEED: list[dict[str, Any]] = [
    {
        "id": 1,
        "status": "待认领",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-A",
        "字段": "账户号",
        "检查项": "账户号格式",
        "规则编号": "QUAL-ACCT-FMT",
        "归因规则修订号": 1,
        "复查范围": "逐项待办",
        "认领人": "",
        "待办来源": "拒绝归因#1",
    },
    {
        "id": 2,
        "status": "待认领",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-A",
        "字段": "账户号",
        "检查项": "账户号空值",
        "规则编号": "QUAL-ACCT-NULL",
        "归因规则修订号": 1,
        "复查范围": "逐项待办",
        "认领人": "",
        "待办来源": "拒绝归因#2",
    },
    {
        "id": 3,
        "status": "待认领",
        "pending": True,
        "abnormal": True,
        "批次编号": "BATC-0101",
        "源键": "SRC-B",
        "字段": "账户号",
        "检查项": "账户号格式",
        "规则编号": "QUAL-ACCT-FMT",
        "归因规则修订号": 1,
        "复查范围": "逐项待办",
        "认领人": "",
        "待办来源": "拒绝归因#3",
    },
]

# 运行期填充的表，初始留空。
QC_REVIEW_CONCLUSION_SEED: list[dict[str, Any]] = []
QC_RESEND_RECORD_SEED: list[dict[str, Any]] = []
QC_RULE_BACKTEST_SEED: list[dict[str, Any]] = []
QC_BATCH_RECOMPUTE_SEED: list[dict[str, Any]] = []

REJECTION_TABLES: dict[str, list[dict[str, Any]]] = {
    "qc_rule_revision": QC_RULE_REVISION_SEED,
    "qc_batch": QC_BATCH_SEED,
    "qc_source_row": QC_SOURCE_ROW_SEED,
    "qc_reject_attr": QC_REJECT_ATTR_SEED,
    "qc_review_todo": QC_REVIEW_TODO_SEED,
    "qc_review_conclusion": QC_REVIEW_CONCLUSION_SEED,
    "qc_resend_record": QC_RESEND_RECORD_SEED,
    "qc_rule_backtest": QC_RULE_BACKTEST_SEED,
    "qc_batch_recompute": QC_BATCH_RECOMPUTE_SEED,
}
