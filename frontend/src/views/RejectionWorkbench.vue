<template>
  <section class="page" data-module="rejection">
    <header class="page-head">
      <div>
        <h2>逐行拒绝归因工作台</h2>
        <p class="page-desc">
          从接入任务追查被拒源行实际命中的字段与检查项（含规则修订号），质量工作台逐项认领更正，
          接入入口按现用规则逐项通过依据决定重送是否接收。
        </p>
      </div>
    </header>

    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">去重拒绝行数</span>
        <strong class="stat-value">{{ snapshot['去重拒绝行数'] ?? attrPage.summary?.distinct_rejected_rows ?? 0 }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">归因明细（含一项多因）</span>
        <strong class="stat-value">{{ attrPage.summary?.attribution_records ?? 0 }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">待认领逐项待办</span>
        <strong class="stat-value">{{ snapshot['待认领待办'] ?? 0 }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">重送 / 回测 / 重算</span>
        <strong class="stat-value">
          {{ snapshot['重送记录数'] ?? 0 }} / {{ snapshot['回测次数'] ?? 0 }} / {{ snapshot['重算次数'] ?? 0 }}
        </strong>
      </article>
    </div>

    <nav class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        :data-testid="`tab-${tab.key}`"
        type="button"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <p v-if="message" class="flash" :class="messageOk ? 'flash-ok' : 'flash-err'" data-testid="flash">
      {{ message }}
    </p>

    <!-- ============ 1. 逐行拒绝归因 ============ -->
    <div v-if="activeTab === 'attribution'">
      <form class="filter-bar" @submit.prevent="loadAttributions">
        <label class="filter-item">
          <span>批次编号</span>
          <input v-model="attrFilter.批次编号" data-testid="filter-batch" placeholder="如 BATC-0101" />
        </label>
        <label class="filter-item">
          <span>源键</span>
          <input v-model="attrFilter.源键" data-testid="filter-source" placeholder="按源键检索" />
        </label>
        <label class="filter-item">
          <span>字段</span>
          <input v-model="attrFilter.字段" data-testid="filter-field" placeholder="按触发字段筛选" />
        </label>
        <label class="filter-item">
          <span>检查项</span>
          <input v-model="attrFilter.检查项" data-testid="filter-check" placeholder="如 账户号空值" />
        </label>
        <button class="btn primary" data-testid="attr-query" type="submit">查询归因</button>
        <button class="btn ghost" type="button" @click="resetAttrFilter">重置</button>
      </form>
      <p class="caliber-note" data-testid="caliber-note">
        口径：{{ attrPage.summary?.caliber ?? '源键去重' }}；去重拒绝量 {{ attrPage.summary?.distinct_rejected_rows ?? 0 }}，
        归因明细 {{ attrPage.summary?.attribution_records ?? 0 }} 条。
      </p>
      <table class="data-table">
        <thead>
          <tr>
            <th>批次编号</th><th>源键</th><th>行号</th><th>触发字段</th>
            <th>命中检查项（含规则修订号）</th><th>原因数</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in attrPage.items" :key="row.源键" :data-testid="`attr-row-${row.源键}`">
            <td>{{ row.批次编号 }}</td>
            <td>{{ row.源键 }}</td>
            <td>{{ row.行号 }}</td>
            <td>{{ row.字段 }}</td>
            <td>
              <span v-for="rev in row.命中规则修订" :key="rev" class="tag">{{ rev }}</span>
            </td>
            <td>{{ row.拒绝原因数 }}</td>
            <td>
              <button class="link" type="button" :data-testid="`detail-${row.源键}`" @click="openDetail(row)">
                查看逐行档案
              </button>
            </td>
          </tr>
          <tr v-if="!attrPage.items.length">
            <td colspan="7" class="empty-state">暂无归因数据</td>
          </tr>
        </tbody>
      </table>
      <footer class="page-foot">
        <span>共 {{ attrPage.total }} 个去重源键（实际拒绝量口径）</span>
        <span>第 {{ attrPage.page }} 页 / 每页 {{ attrPage.size }} 条</span>
      </footer>
    </div>

    <!-- ============ 2. 质量工作台逐项待办 ============ -->
    <div v-if="activeTab === 'workbench'">
      <p class="caliber-note" data-testid="todo-granularity">
        待办粒度：{{ todoPage.todo_granularity ?? '逐项待办' }}——每个命中检查项一条，不要求整行复查。
      </p>
      <form class="filter-bar" @submit.prevent="loadTodos">
        <label class="filter-item">
          <span>源键</span>
          <input v-model="todoFilter.源键" placeholder="按源键筛选" />
        </label>
        <label class="filter-item">
          <span>检查项</span>
          <input v-model="todoFilter.检查项" placeholder="如 账户号格式" />
        </label>
        <label class="filter-item">
          <span>状态</span>
          <input v-model="todoFilter.status" placeholder="待认领/已认领/更正已提交" />
        </label>
        <button class="btn primary" type="submit">查询待办</button>
        <button class="btn ghost" type="button" @click="resetTodoFilter">重置</button>
      </form>
      <table class="data-table">
        <thead>
          <tr>
            <th>源键</th><th>字段</th><th>检查项</th><th>规则/归因修订</th>
            <th>状态</th><th>认领人</th><th>复查模式</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="todo in todoPage.items" :key="todo.id" :data-testid="`todo-row-${todo.id}`">
            <td>{{ todo.源键 }}</td>
            <td>{{ todo.字段 }}</td>
            <td>{{ todo.检查项 }}</td>
            <td>{{ todo.规则编号 }}#{{ todo.归因规则修订号 }}</td>
            <td>{{ todo.status }}<span v-if="todo.待重跑原因" class="tag warn">{{ todo.待重跑原因 }}</span></td>
            <td>{{ todo.认领人 || '—' }}</td>
            <td>{{ todo.复查模式 || '—' }}</td>
            <td class="row-actions">
              <button
                v-if="todo.status === '待认领'"
                class="link"
                type="button"
                :data-testid="`claim-${todo.id}`"
                @click="openClaim(todo)"
              >认领</button>
              <button
                v-if="todo.status === '已认领'"
                class="link"
                type="button"
                :data-testid="`correct-${todo.id}`"
                @click="openCorrection(todo)"
              >提交更正</button>
            </td>
          </tr>
          <tr v-if="!todoPage.items.length">
            <td colspan="8" class="empty-state">暂无待办</td>
          </tr>
        </tbody>
      </table>
      <footer class="page-foot"><span>共 {{ todoPage.total }} 条逐项待办</span></footer>
    </div>

    <!-- ============ 3. 规则修订 ============ -->
    <div v-if="activeTab === 'rules'">
      <div class="filter-bar">
        <label class="filter-item">
          <span>规则编号</span>
          <input v-model="ruleFilter" placeholder="留空查看全部规则" />
        </label>
        <button class="btn primary" type="button" @click="loadRules">查询修订</button>
        <button class="btn" type="button" data-testid="open-publish" @click="openPublish">发布新修订</button>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>规则编号</th><th>检查项</th><th>字段</th><th>修订号</th>
            <th>检查类型</th><th>规则内容</th><th>状态</th><th>现用</th><th>生效时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rev in rulePage.items" :key="rev.id" :data-testid="`rule-row-${rev.id}`">
            <td>{{ rev.规则编号 }}</td>
            <td>{{ rev.检查项 }}</td>
            <td>{{ rev.检查字段 }}</td>
            <td>#{{ rev.修订号 }}</td>
            <td>{{ rev.检查类型 }}</td>
            <td>{{ rev.规则内容 }}</td>
            <td>{{ rev.status }}</td>
            <td>
              <span :class="['tag', rev.是否现用 ? 'ok' : 'muted']">
                {{ rev.是否现用 ? '现用' : '历史留档' }}
              </span>
            </td>
            <td>{{ rev.生效时间 }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ============ 4. 接入入口重送 ============ -->
    <div v-if="activeTab === 'resend'">
      <form class="filter-bar" @submit.prevent="doResend">
        <label class="filter-item">
          <span>批次编号</span>
          <input v-model="resendForm.batch" placeholder="BATC-0101" required />
        </label>
        <label class="filter-item">
          <span>源键</span>
          <input v-model="resendForm.source" placeholder="SRC-A" required />
        </label>
        <label class="filter-item">
          <span>操作人</span>
          <input v-model="resendForm.operator" placeholder="接入入口" />
        </label>
        <button class="btn primary" data-testid="submit-resend" type="submit">重送源行</button>
      </form>
      <p class="caliber-note">
        接入端独立复算：仅当该源键命中的每项现用规则都有与现用修订一致的逐项通过依据时才接收，否则当次拒收。
      </p>
      <div v-if="lastResend" class="result-card" data-testid="resend-result">
        <h4>重送结果：{{ lastResend.status }}（源键 {{ lastResend.源键 }}）</h4>
        <table class="data-table">
          <thead>
            <tr><th>检查项</th><th>现用修订</th><th>通过依据</th><th>接入端复算</th><th>判定</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in lastResend.逐项判定" :key="c.规则编号">
              <td>{{ c.检查项 }}</td>
              <td>#{{ c.现用修订号 }}</td>
              <td>{{ c.通过依据 }}</td>
              <td>{{ c.接入端复算 }}</td>
              <td>
                <span :class="['tag', c.接收判定 === '通过' ? 'ok' : 'warn']">{{ c.接收判定 }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="lastResend.拒收原因" class="error-text">拒收原因：{{ lastResend.拒收原因 }}</p>
      </div>
    </div>

    <!-- ============ 5. 规则回测 ============ -->
    <div v-if="activeTab === 'backtest'">
      <form class="filter-bar" @submit.prevent="doBacktest">
        <label class="filter-item">
          <span>规则编号</span>
          <input v-model="backtestForm.ruleNo" placeholder="QUAL-ACCT-NULL" required />
        </label>
        <label class="filter-item">
          <span>修订号</span>
          <input v-model.number="backtestForm.revisionNo" type="number" min="1" required />
        </label>
        <label class="filter-item">
          <span>批次（可空）</span>
          <input v-model="backtestForm.batchNo" placeholder="BATC-0101" />
        </label>
        <button class="btn primary" data-testid="submit-backtest" type="submit">运行回测</button>
      </form>
      <table class="data-table">
        <thead>
          <tr>
            <th>规则编号</th><th>回测修订</th><th>批次</th><th>样本行</th>
            <th>拒绝行</th><th>通过行</th><th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bt in backtests" :key="bt.id">
            <td>{{ bt.规则编号 }}</td>
            <td>#{{ bt.回测修订号 }}</td>
            <td>{{ bt.回测批次 }}</td>
            <td>{{ bt.样本行数 }}</td>
            <td>{{ bt.拒绝行数 }}</td>
            <td>{{ bt.通过行数 }}</td>
            <td>{{ bt.回测时间 }}</td>
          </tr>
          <tr v-if="!backtests.length"><td colspan="7" class="empty-state">暂无回测结果</td></tr>
        </tbody>
      </table>
    </div>

    <!-- ============ 6. 旧批重算对照 ============ -->
    <div v-if="activeTab === 'recompute'">
      <form class="filter-bar" @submit.prevent="doRecompute">
        <label class="filter-item">
          <span>批次编号</span>
          <input v-model="recomputeBatchNo" placeholder="BATC-0101" required />
        </label>
        <button class="btn primary" data-testid="submit-recompute" type="submit">按现口径重算对照</button>
      </form>
      <p class="caliber-note">原接入任务按当时口径留档；重算只追加对照，不覆盖原字段映射与拒绝依据。</p>
      <div v-for="rc in recomputes" :key="rc.id" class="result-card" data-testid="recompute-card">
        <h4>批次 {{ rc.批次编号 }}：原口径 v{{ rc.原口径版本 }}</h4>
        <p>
          原拒绝 {{ rc.原拒绝行数 }} 行 → 现口径拒绝 {{ rc.现口径拒绝行数 }} 行；
          原字段映射：{{ rc.原字段映射 }}；原拒绝依据可查：{{ rc.原拒绝依据可查 ? '是' : '否' }}
        </p>
        <table class="data-table">
          <thead><tr><th>源键</th><th>现口径拒绝项</th><th>现口径判定</th></tr></thead>
          <tbody>
            <tr v-for="line in rc.逐行对照" :key="line.源键">
              <td>{{ line.源键 }}</td>
              <td>
                <span v-for="item in line.现口径拒绝项" :key="item" class="tag warn">{{ item }}</span>
                <span v-if="!line.现口径拒绝项.length" class="muted">—</span>
              </td>
              <td>{{ line.现口径判定 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!recomputes.length" class="empty-state">暂无重算对照</p>
    </div>

    <!-- ============ 归因详情弹窗 ============ -->
    <div v-if="detail" class="modal-backdrop" data-testid="detail-modal">
      <div class="modal wide">
        <h3>源行逐行档案 · {{ detail.源键 }}（{{ detail.批次编号 }}）</h3>
        <dl v-if="detail.源行" class="detail-grid">
          <dt>行号</dt><dd>{{ detail.源行.行号 }}</dd>
          <dt>原始值</dt><dd>{{ detail.源行.原始值 }}</dd>
          <dt>转换值</dt><dd>{{ detail.源行.转换值 || '（空）' }}</dd>
          <dt>转换规则</dt><dd>{{ detail.源行.转换规则修订 }}</dd>
          <dt>当前接收</dt><dd>{{ detail.源行.当前接收状态 }}</dd>
        </dl>
        <h4>逐项拒绝归因（带规则修订号）</h4>
        <table class="data-table">
          <thead><tr><th>字段</th><th>检查项</th><th>规则修订</th><th>拒绝依据</th><th>触发阶段</th></tr></thead>
          <tbody>
            <tr v-for="a in detail.归因明细" :key="a.id">
              <td>{{ a.字段 }}</td>
              <td>{{ a.检查项 }}</td>
              <td>{{ a.规则编号 }}#{{ a.规则修订号 }}</td>
              <td>{{ a.拒绝依据 }}</td>
              <td>{{ a.触发阶段 }}</td>
            </tr>
          </tbody>
        </table>
        <h4>复查结论 / 重送记录（同一源键关联）</h4>
        <p v-for="c in detail.复查结论" :key="c.id" class="record-line">
          <span class="tag" :class="c.检查结果 === '通过' ? 'ok' : 'warn'">{{ c.检查结果 }}</span>
          {{ c.检查项 }} 按 {{ c.规则编号 }}#{{ c.执行规则修订号 }}（{{ c.复查模式 }}）— {{ c.复查时间 }}
        </p>
        <p v-for="r in detail.重送记录" :key="r.id" class="record-line">
          <span class="tag" :class="r.status === '已接收' ? 'ok' : 'warn'">{{ r.status }}</span>
          重送于 {{ r.重送时间 }}（{{ r.操作人 }}）
        </p>
        <p v-if="!detail.复查结论.length && !detail.重送记录.length" class="muted">暂无复查与重送记录</p>
        <div class="page-actions"><button class="btn primary" type="button" @click="detail = null">关闭</button></div>
      </div>
    </div>

    <!-- ============ 认领弹窗 ============ -->
    <div v-if="claimTarget" class="modal-backdrop">
      <form class="modal" @submit.prevent="doClaim">
        <h3>认领逐项待办 · {{ claimTarget.检查项 }}（{{ claimTarget.源键 }}）</h3>
        <label class="create-field">
          <span>认领人</span>
          <input v-model="claimAssignee" data-testid="claim-assignee" required />
        </label>
        <p class="muted">该待办仅覆盖单个检查项「{{ claimTarget.检查项 }}」，无需整行复查。</p>
        <div class="page-actions">
          <button class="btn" type="button" @click="claimTarget = null">取消</button>
          <button class="btn primary" data-testid="confirm-claim" type="submit">确认认领</button>
        </div>
      </form>
    </div>

    <!-- ============ 更正弹窗 ============ -->
    <div v-if="correctTarget" class="modal-backdrop">
      <form class="modal" @submit.prevent="doCorrection">
        <h3>提交逐项更正 · {{ correctTarget.检查项 }}（{{ correctTarget.源键 }}）</h3>
        <label class="create-field">
          <span>更正后原始值</span>
          <input v-model="correctionForm.raw" data-testid="correct-raw" required />
        </label>
        <label class="create-field">
          <span>更正后转换值</span>
          <input v-model="correctionForm.converted" data-testid="correct-converted" />
        </label>
        <label class="create-field">
          <span>备注</span>
          <input v-model="correctionForm.remark" />
        </label>
        <p class="muted">
          提交后按规则是否改版决定：未改版沿用仍有效的逐项结论，已改版则按现用修订重跑这一项。
        </p>
        <div class="page-actions">
          <button class="btn" type="button" @click="correctTarget = null">取消</button>
          <button class="btn primary" data-testid="confirm-correction" type="submit">提交更正</button>
        </div>
      </form>
    </div>

    <!-- ============ 发布修订弹窗 ============ -->
    <div v-if="showPublish" class="modal-backdrop">
      <form class="modal" @submit.prevent="doPublish">
        <h3>发布规则新修订</h3>
        <label class="create-field">
          <span>规则编号</span>
          <input v-model="publishForm.ruleNo" data-testid="publish-rule-no" required />
        </label>
        <label class="create-field">
          <span>检查类型（留空沿用）</span>
          <input v-model="publishForm.checkType" placeholder="如 空值校验" />
        </label>
        <label class="create-field">
          <span>新规则内容</span>
          <input v-model="publishForm.ruleContent" data-testid="publish-content" required />
        </label>
        <p class="muted">发布后最高生效修订成为现用规则，旧修订留档；该规则的已提交待办会退回待认领重跑。</p>
        <div class="page-actions">
          <button class="btn" type="button" @click="showPublish = false">取消</button>
          <button class="btn primary" data-testid="confirm-publish" type="submit">发布修订</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import {
  claimTodo,
  fetchAttributionDetail,
  fetchAttributions,
  fetchBacktests,
  fetchBatches,
  fetchRecomputes,
  fetchRuleRevisions,
  fetchSnapshot,
  fetchTodos,
  publishRevision,
  recomputeBatch,
  resendRow,
  runBacktest,
  submitCorrection,
} from '@/api/rejection-service'

type TabKey = 'attribution' | 'workbench' | 'rules' | 'resend' | 'backtest' | 'recompute'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'attribution', label: '逐行拒绝归因' },
  { key: 'workbench', label: '质量工作台' },
  { key: 'rules', label: '规则修订' },
  { key: 'resend', label: '接入入口重送' },
  { key: 'backtest', label: '规则回测' },
  { key: 'recompute', label: '旧批重算对照' },
]
const activeTab = ref<TabKey>('attribution')
const message = ref('')
const messageOk = ref(true)
const snapshot = ref<Record<string, number>>({})

function flash(text: string, ok = true) {
  message.value = text
  messageOk.value = ok
}

// ---- 归因 ----
type AttrRow = {
  批次编号: string
  源键: string
  行号: number
  字段: string
  命中检查项: string[]
  命中规则修订: string[]
  拒绝原因数: number
}
const attrFilter = reactive({ 批次编号: 'BATC-0101', 源键: '', 字段: '', 检查项: '' })
const attrPage = ref<{
  items: AttrRow[]
  total: number
  page: number
  size: number
  summary?: { distinct_rejected_rows: number; attribution_records: number; caliber: string }
}>({ items: [], total: 0, page: 1, size: 20 })
const detail = ref<any>(null)

async function loadAttributions() {
  try {
    attrPage.value = await fetchAttributions({
      batch_no: attrFilter.批次编号,
      source_key: attrFilter.源键,
      field: attrFilter.字段,
      check_item: attrFilter.检查项,
    })
  } catch (error) {
    flash(error instanceof Error ? error.message : '归因查询失败', false)
  }
}

function resetAttrFilter() {
  attrFilter.批次编号 = ''
  attrFilter.源键 = ''
  attrFilter.字段 = ''
  attrFilter.检查项 = ''
  void loadAttributions()
}

async function openDetail(row: AttrRow) {
  detail.value = await fetchAttributionDetail(row.批次编号, row.源键)
}

// ---- 工作台 ----
const todoFilter = reactive({ 源键: '', 检查项: '', status: '' })
const todoPage = ref<{ items: any[]; total: number; todo_granularity?: string }>({ items: [], total: 0 })
const claimTarget = ref<any | null>(null)
const claimAssignee = ref('')
const correctTarget = ref<any | null>(null)
const correctionForm = reactive({ raw: '', converted: '', remark: '' })

async function loadTodos() {
  try {
    todoPage.value = await fetchTodos({
      source_key: todoFilter.源键,
      check_item: todoFilter.检查项,
      status: todoFilter.status,
    })
  } catch (error) {
    flash(error instanceof Error ? error.message : '待办查询失败', false)
  }
}

function resetTodoFilter() {
  todoFilter.源键 = ''
  todoFilter.检查项 = ''
  todoFilter.status = ''
  void loadTodos()
}

function openClaim(todo: any) {
  claimTarget.value = todo
  claimAssignee.value = ''
}

async function doClaim() {
  if (!claimTarget.value) return
  const result = await claimTodo(claimTarget.value.id, claimAssignee.value)
  flash(result.message, result.ok)
  claimTarget.value = null
  await loadTodos()
  await loadSnapshot()
}

function openCorrection(todo: any) {
  correctTarget.value = todo
  correctionForm.raw = ''
  correctionForm.converted = ''
  correctionForm.remark = ''
}

async function doCorrection() {
  if (!correctTarget.value) return
  const result = await submitCorrection(
    correctTarget.value.id,
    correctionForm.raw,
    correctionForm.converted,
    correctionForm.remark,
  )
  flash(result.message, result.ok)
  correctTarget.value = null
  await loadTodos()
}

// ---- 规则修订 ----
const ruleFilter = ref('')
const rulePage = ref<{ items: any[]; total: number }>({ items: [], total: 0 })
const showPublish = ref(false)
const publishForm = reactive({ ruleNo: '', checkType: '', ruleContent: '' })

async function loadRules() {
  rulePage.value = await fetchRuleRevisions(ruleFilter.value)
}

function openPublish() {
  publishForm.ruleNo = ''
  publishForm.checkType = ''
  publishForm.ruleContent = ''
  showPublish.value = true
}

async function doPublish() {
  const result = await publishRevision(
    publishForm.ruleNo,
    publishForm.ruleContent,
    publishForm.checkType,
  )
  flash(result.message, result.ok)
  showPublish.value = false
  await loadRules()
  await loadTodos()
  await loadSnapshot()
}

// ---- 重送 ----
const resendForm = reactive({ batch: 'BATC-0101', source: '', operator: '接入入口' })
const lastResend = ref<any | null>(null)

async function doResend() {
  const result = await resendRow(resendForm.batch, resendForm.source, resendForm.operator)
  lastResend.value = result.entry
  flash(result.message, result.ok)
  await loadAttributions()
  await loadSnapshot()
}

// ---- 回测 ----
const backtestForm = reactive({ ruleNo: 'QUAL-ACCT-NULL', revisionNo: 1, batchNo: 'BATC-0101' })
const backtests = ref<any[]>([])

async function loadBacktests() {
  backtests.value = (await fetchBacktests()).items
}

async function doBacktest() {
  const result = await runBacktest(
    backtestForm.ruleNo,
    Number(backtestForm.revisionNo),
    backtestForm.batchNo,
  )
  flash(result.message, result.ok)
  await loadBacktests()
}

// ---- 重算 ----
const recomputeBatchNo = ref('BATC-0101')
const recomputes = ref<any[]>([])

async function loadRecomputes() {
  recomputes.value = (await fetchRecomputes()).items
}

async function doRecompute() {
  const result = await recomputeBatch(recomputeBatchNo.value)
  flash(result.message, result.ok)
  await loadRecomputes()
}

// ---- 快照与切换 ----
async function loadSnapshot() {
  snapshot.value = await fetchSnapshot()
  // 派生一个去重拒绝行数指标，避免后端快照字段与页面卡片命名耦合。
  if (snapshot.value['归因记录数'] !== undefined) {
    snapshot.value['去重拒绝行数'] = attrPage.value.summary?.distinct_rejected_rows ?? 0
  }
}

async function switchTab(key: TabKey) {
  activeTab.value = key
  if (key === 'workbench') await loadTodos()
  if (key === 'rules') await loadRules()
  if (key === 'backtest') await loadBacktests()
  if (key === 'recompute') await loadRecomputes()
}

onMounted(async () => {
  await fetchBatches()
  await loadAttributions()
  await loadSnapshot()
})
</script>

<style scoped>
.tab-bar { display: flex; gap: 8px; margin: 8px 0 14px; flex-wrap: wrap; }
.tab-btn { border: 1px solid var(--border); background: #fff; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 13px; }
.tab-btn.active { background: var(--brand); border-color: var(--brand); color: #fff; }
.caliber-note { font-size: 12px; color: var(--muted); background: #fff; border: 1px dashed var(--border); border-radius: 6px; padding: 8px 10px; }
.tag { display: inline-block; font-size: 11px; padding: 2px 6px; border-radius: 10px; background: #eef2ff; color: #3730a3; margin: 1px 3px 1px 0; }
.tag.ok { background: #dcfce7; color: #166534; }
.tag.warn { background: #fee2e2; color: #991b1b; }
.tag.muted { background: #f1f5f9; color: var(--muted); }
.flash { padding: 8px 12px; border-radius: 6px; font-size: 13px; }
.flash-ok { background: #dcfce7; color: #166534; }
.flash-err { background: #fee2e2; color: #991b1b; }
.result-card { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin: 12px 0; }
.modal.wide { width: min(860px, 100%); }
.detail-grid { display: grid; grid-template-columns: 120px 1fr 120px 1fr; gap: 6px 10px; font-size: 13px; }
.detail-grid dt { color: var(--muted); }
.detail-grid dd { margin: 0; }
.record-line { font-size: 13px; display: flex; align-items: center; gap: 8px; }
.muted { color: var(--muted); }
</style>
