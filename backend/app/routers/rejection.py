"""逐行拒绝归因路由：接入任务 → 归因检索 → 工作台认领更正 → 重送闭环 → 回测/重算。

独立于通用 /api/{module} 资源路由，固定路径在资源路由之前注册，避免被动态路径抢先匹配。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.rejection import rejection_service

router = APIRouter(prefix="/api/rejection", tags=["逐行拒绝归因"])


class ClaimPayload(BaseModel):
    assignee: str


class CorrectionPayload(BaseModel):
    corrected_raw: str = ""
    corrected_converted: str = ""
    remark: str | None = None


class RevisionPayload(BaseModel):
    rule_content: str
    check_type: str | None = None


class ResendPayload(BaseModel):
    operator: str = "接入入口"


@router.get("/batches")
def get_batches() -> dict[str, Any]:
    return {"items": rejection_service.list_batches(), "total": len(rejection_service.list_batches())}


@router.get("/attributions")
def get_attributions(
    batch_no: str | None = Query(default=None),
    source_key: str | None = Query(default=None),
    field: str | None = Query(default=None),
    check_item: str | None = Query(default=None),
    rule_no: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    items, total, summary = rejection_service.list_attributions(
        batch_no=batch_no, source_key=source_key, field=field, check_item=check_item,
        rule_no=rule_no, page=page, size=size,
    )
    return {"items": items, "total": total, "page": page, "size": size, "summary": summary}


@router.get("/attributions/{batch_no}/{source_key}")
def get_attribution_detail(batch_no: str, source_key: str) -> dict[str, Any]:
    return rejection_service.attribution_detail(batch_no, source_key)


@router.get("/todos")
def get_todos(
    batch_no: str | None = Query(default=None),
    source_key: str | None = Query(default=None),
    check_item: str | None = Query(default=None),
    status: str | None = Query(default=None),
    assignee: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    items, total = rejection_service.list_todos(
        batch_no=batch_no, source_key=source_key, check_item=check_item,
        status=status, assignee=assignee, page=page, size=size,
    )
    return {"items": items, "total": total, "page": page, "size": size,
            "todo_granularity": "逐项待办：每个命中检查项一条，不要求整行复查"}


@router.post("/todos/{todo_id}/claim")
def claim_todo(todo_id: int, payload: ClaimPayload) -> dict[str, Any]:
    entry, message = rejection_service.claim_todo(todo_id, payload.assignee)
    return {"ok": entry is not None, "message": message, "entry": entry}


@router.post("/todos/{todo_id}/correction")
def submit_correction(todo_id: int, payload: CorrectionPayload) -> dict[str, Any]:
    entry, message = rejection_service.submit_correction(
        todo_id,
        corrected_raw=payload.corrected_raw,
        corrected_converted=payload.corrected_converted,
        remark=payload.remark or "",
    )
    return {"ok": entry is not None, "message": message, "entry": entry}


@router.get("/rules/revisions")
def get_rule_revisions(rule_no: str | None = Query(default=None)) -> dict[str, Any]:
    items = rejection_service.list_rule_revisions(rule_no)
    return {"items": items, "total": len(items)}


@router.post("/rules/{rule_no}/revisions")
def publish_revision(rule_no: str, payload: RevisionPayload) -> dict[str, Any]:
    entry, message = rejection_service.publish_revision(
        rule_no, rule_content=payload.rule_content, check_type=payload.check_type,
    )
    return {"ok": entry is not None, "message": message, "entry": entry}


@router.post("/resend/{batch_no}/{source_key}")
def resend_source_row(batch_no: str, source_key: str, payload: ResendPayload) -> dict[str, Any]:
    entry, message = rejection_service.resend(
        batch_no, source_key, operator=payload.operator,
    )
    return {"ok": entry is not None and entry.get("status") == "已接收",
            "message": message, "entry": entry}


@router.post("/backtest/{rule_no}/{revision_no}")
def run_backtest(
    rule_no: str, revision_no: int, batch_no: str | None = Query(default=None)
) -> dict[str, Any]:
    entry, message = rejection_service.backtest(rule_no, revision_no, batch_no=batch_no)
    return {"ok": entry is not None, "message": message, "entry": entry}


@router.get("/backtest")
def get_backtests(rule_no: str | None = Query(default=None)) -> dict[str, Any]:
    items = rejection_service.list_backtests(rule_no)
    return {"items": items, "total": len(items)}


@router.post("/recompute/{batch_no}")
def recompute_batch(batch_no: str) -> dict[str, Any]:
    entry, message = rejection_service.recompute_batch(batch_no)
    return {"ok": entry is not None, "message": message, "entry": entry}


@router.get("/recompute")
def get_recomputes(batch_no: str | None = Query(default=None)) -> dict[str, Any]:
    items = rejection_service.list_recomputes(batch_no)
    return {"items": items, "total": len(items)}


@router.get("/snapshot")
def get_snapshot() -> dict[str, Any]:
    return rejection_service.snapshot()
