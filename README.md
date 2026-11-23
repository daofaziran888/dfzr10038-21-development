# 特征工坊 · 特征工程与标注数据管理平台

面向特征注册与检索、衍生特征工程、时间窗口计算、特征回溯填充、样本分层抽取、标注任务派发、标注质量审核、特征血缘追踪与在线/离线特征服务的数据特征工程与标注管理平台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/WorkbenchView.vue|tsx  全部模块共享工作台
│   ├── src/data/modules.ts              18个业务模块配置
│   ├── src/api/              统一请求封装
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/resource.py  通用查询/导出/登记/动作接口
│   ├── app/services/<key>.py    每个模块独立领域逻辑
│   ├── app/services/base.py     共享服务骨架
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 特征注册 | `feature_reg` | 特征定义 | 特征编号、特征名称、数据类型 |
| 衍生工程 | `derive_rule` | 衍生规则 | 规则编号、输入特征、衍生函数 |
| 时间窗口 | `time_window` | 窗口模板 | 模板编号、窗口类型、窗口宽度 |
| 特征回溯 | `backfill_job` | 回溯任务 | 任务编号、目标特征、起始日期 |
| 样本分层 | `sample_strata` | 分层策略 | 策略编号、特征范围、分层字段 |
| 标注派发 | `label_task` | 标注任务 | 任务编号、样本范围、标注类型 |
| 标注审核 | `label_review` | 审核批次 | 批次编号、标注任务、审核人 |
| 一致性计算 | `consent_calc` | 一致性报告 | 报告编号、标注任务、评估指标 |
| 特征存储 | `feature_store` | 存储配置 | 配置编号、特征列表、存储引擎 |
| 在线服务 | `online_serv` | 服务端点 | 端点编号、特征列表、QPS上限 |
| 离线导出 | `offline_exp` | 导出管道 | 管道编号、特征范围、导出格式 |
| 特征血缘 | `feature_line` | 血缘链路 | 链路编号、上游特征、下游特征 |
| 特征监控 | `feature_mon` | 监控规则 | 规则编号、目标特征、监控类型 |
| 版本管理 | `version_mgr` | 特征版本 | 版本编号、关联特征、版本标签 |
| 数据切分 | `data_split` | 切分配置 | 配置编号、数据集、切分方式 |
| 特征目录 | `feat_catalog` | 目录索引 | 索引编号、目录名称、父目录 |
| 质量规则 | `quality_rule` | 质量检查 | 规则编号、目标特征、检查类型 |
| 标注词典 | `label_dict` | 标注项 | 词典编号、标签名称、标签值 |
| 批量接入 | `batch_load` | 接入任务 | 任务编号、数据源、目标特征 |
| 特征报告 | `report_task` | 分析报表 | 报告编号、报告类型、特征范围 |
| 调度编排 | `schedule_job` | 调度计划 | 计划编号、任务类型、关联对象 |
| 治理审计 | `govern_audit` | 审计记录 | 记录编号、审计对象、审计类型 |

## 约定

- 全部模块共享`frontend/src/views/WorkbenchView.vue|tsx`和一套资源路由。
- 每个模块仍保留独立`backend/app/services/<模块>.py`；纯前端保留
  `frontend/src/domain/<模块>.ts`，用于承载真实业务差异并维持36题位容量。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

## 逐行拒绝归因闭环（`/rejection`）

接入任务原本只给拒绝总量，没有按源字段追查被拒原始行的入口。该子域补齐
「接入任务 → 逐行拒绝归因 → 质量工作台逐项认领更正 → 接入入口重送」的完整链路，
后端在 `app/services/rejection.py`、路由在 `app/routers/rejection.py`（固定前缀
`/api/rejection`，先于通用 `/{module}` 动态路由注册），示例数据在 `app/rejection_seed.py`，
前端为 `frontend/src/views/RejectionWorkbench.vue`。

关键口径与能力：

- **源键去重口径**：同一源键可同时命中多项检查（如账户号格式 + 转换后空值），
  归因明细按「源键 × 字段 × 检查项 × 规则修订号」逐条记录，但按字段筛选与翻页时
  `total` 按源键去重，只计一行，与实际拒绝量一致。
- **逐项待办而非整行复查**：每个命中检查项生成一条待办（`todo_granularity` 标注），
  质量员只认领并更正单个检查项；规则未改版时复查沿用仍有效的逐项结论，
  规则改版后该规则的已提交待办自动退回待认领，按现用修订重跑这一项。
- **规则修订留档**：同一规则编号多修订号，最高生效修订为现用规则，旧修订留档可查；
  支持指定修订号回测（`/backtest/{rule}/{revision}`）。
- **重送门禁**：接入端独立复算，仅当该源键命中的每项现用规则都有与现用修订一致的
  逐项通过依据时才接收，否则当次拒收并给出仍生效的失败检查项。
- **旧批留档与重算**：原批次按当时口径（字段映射、规则修订基线、口径版本）留档；
  口径调整后只追加对照重算（`/recompute/{batch}`），原字段映射与拒绝依据仍可查。

示例故事：源键 `SRC-A` 同时命中账户号格式与空值、`SRC-B` 只命中旧格式；首轮只解除
A 的空值时重送当次拒收，补齐格式前先把空值校验改版，最终重送仅在现用规则逐项都有
通过依据时成功。`/tmp/rejection_e2e/e2e_rejection.py` 覆盖该故事的 60 项断言。

领域：数据工程
子方向：数仓与数据湖
