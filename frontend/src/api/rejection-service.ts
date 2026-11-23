/** 逐行拒绝归因子域的接口封装：归因检索、工作台认领更正、重送、回测、重算。 */
import { request } from './client'

export type AttrGroup = {
  批次编号: string
  源键: string
  行号: number
  字段: string
  命中检查项: string[]
  命中规则修订: string[]
  拒绝原因数: number
}

export type AttrPage = {
  items: AttrGroup[]
  total: number
  page: number
  size: number
  summary: {
    distinct_rejected_rows: number
    attribution_records: number
    caliber: string
  }
}

export type ReviewTodo = {
  id: number
  status: string
  批次编号: string
  源键: string
  字段: string
  检查项: string
  规则编号: string
  归因规则修订号: number
  复查范围: string
  认领人: string
  待办来源?: string
  待重跑原因?: string
  [key: string]: string | number | boolean | undefined
}

export type RuleRevision = {
  id: number
  status: string
  规则编号: string
  检查项: string
  检查字段: string
  修订号: number
  是否现用: boolean
  检查类型: string
  规则内容: string
  阻断级别: string
  生效时间: string
}

type GenericResult<T> = { ok: boolean; message: string; entry: T }

async function getJson<T>(path: string): Promise<T> {
  const response = await request(`/api/rejection${path}`)
  if (!response.ok) throw new Error('逐行拒绝归因数据读取失败')
  return (await response.json()) as T
}

async function postJson<T>(path: string, body: Record<string, unknown>): Promise<GenericResult<T>> {
  const response = await request(`/api/rejection${path}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return (await response.json()) as GenericResult<T>
}

export function fetchAttributions(filters: Record<string, string>): Promise<AttrPage> {
  const query = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value.trim() !== ''),
  ).toString()
  return getJson<AttrPage>(`/attributions?${query}`)
}

export function fetchAttributionDetail(batchNo: string, sourceKey: string) {
  return getJson<Record<string, any>>(
    `/attributions/${encodeURIComponent(batchNo)}/${encodeURIComponent(sourceKey)}`,
  )
}

export function fetchTodos(filters: Record<string, string> = {}) {
  const query = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value.trim() !== ''),
  ).toString()
  return getJson<{ items: ReviewTodo[]; total: number; todo_granularity: string }>(
    `/todos?${query}`,
  )
}

export function claimTodo(todoId: number, assignee: string) {
  return postJson(`/todos/${todoId}/claim`, { assignee })
}

export function submitCorrection(
  todoId: number,
  correctedRaw: string,
  correctedConverted: string,
  remark: string,
) {
  return postJson(`/todos/${todoId}/correction`, {
    corrected_raw: correctedRaw,
    corrected_converted: correctedConverted,
    remark,
  })
}

export function fetchRuleRevisions(ruleNo = '') {
  const suffix = ruleNo ? `?rule_no=${encodeURIComponent(ruleNo)}` : ''
  return getJson<{ items: RuleRevision[]; total: number }>(`/rules/revisions${suffix}`)
}

export function publishRevision(ruleNo: string, ruleContent: string, checkType: string) {
  return postJson(`/rules/${encodeURIComponent(ruleNo)}/revisions`, {
    rule_content: ruleContent,
    check_type: checkType || null,
  })
}

export function resendRow(batchNo: string, sourceKey: string, operator: string) {
  return postJson(`/resend/${encodeURIComponent(batchNo)}/${encodeURIComponent(sourceKey)}`, {
    operator,
  })
}

export function runBacktest(ruleNo: string, revisionNo: number, batchNo: string) {
  const suffix = batchNo ? `?batch_no=${encodeURIComponent(batchNo)}` : ''
  return postJson(`/backtest/${encodeURIComponent(ruleNo)}/${revisionNo}${suffix}`, {})
}

export function fetchBacktests() {
  return getJson<{ items: Record<string, unknown>[]; total: number }>('/backtest')
}

export function recomputeBatch(batchNo: string) {
  return postJson(`/recompute/${encodeURIComponent(batchNo)}`, {})
}

export function fetchRecomputes() {
  return getJson<{ items: Record<string, unknown>[]; total: number }>('/recompute')
}

export function fetchBatches() {
  return getJson<{ items: Record<string, unknown>[]; total: number }>('/batches')
}

export function fetchSnapshot() {
  return getJson<Record<string, number>>('/snapshot')
}
