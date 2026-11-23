<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">特征工坊 · 特征工程与标注数据管理平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向特征注册与检索、衍生特征工程、时间窗口计算、特征回溯填充、样本分层抽取、标注任务派发、标注质量审核、特征血缘追踪与在线/离线特征服务的数据特征工程与标注管理平台。</span>
        <span class="head-user">当前值班：数据工程组</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
const navItems = [{ label: "运营概览", path: "/" }, { label: "逐行拒绝归因", path: "/rejection" }, { label: "特征注册", path: "/feature_reg" }, { label: "衍生工程", path: "/derive_rule" }, { label: "时间窗口", path: "/time_window" }, { label: "特征回溯", path: "/backfill_job" }, { label: "样本分层", path: "/sample_strata" }, { label: "标注派发", path: "/label_task" }, { label: "标注审核", path: "/label_review" }, { label: "一致性计算", path: "/consent_calc" }, { label: "特征存储", path: "/feature_store" }, { label: "在线服务", path: "/online_serv" }, { label: "离线导出", path: "/offline_exp" }, { label: "特征血缘", path: "/feature_line" }, { label: "特征监控", path: "/feature_mon" }, { label: "版本管理", path: "/version_mgr" }, { label: "数据切分", path: "/data_split" }, { label: "特征目录", path: "/feat_catalog" }, { label: "质量规则", path: "/quality_rule" }, { label: "标注词典", path: "/label_dict" }, { label: "批量接入", path: "/batch_load" }, { label: "特征报告", path: "/report_task" }, { label: "调度编排", path: "/schedule_job" }, { label: "治理审计", path: "/govern_audit" }]
</script>
