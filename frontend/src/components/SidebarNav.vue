<script setup lang="ts">
import { computed } from "vue";

import { formatDateTime, getModeLabel, getStatusLabel, summarizeText } from "@/lib/report";
import type { HealthData, ReportDetailResponse, ReportHistoryItem, SkillCatalog } from "@/types/api";
import type { AnalysisForm, WorkspaceStatus } from "@/types/workspace";

const props = defineProps<{
  form: AnalysisForm;
  status: WorkspaceStatus;
  busy: boolean;
  cacheClearing: boolean;
  report: ReportDetailResponse | null;
  history: ReportHistoryItem[];
  health: HealthData | null;
  skillCatalog: SkillCatalog;
  collapsed: boolean;
}>();

const emit = defineEmits<{
  (event: "new-analysis"): void;
  (event: "fill-example"): void;
  (event: "clear-inputs"): void;
  (event: "clear-history"): void;
  (event: "select-report", taskId: string): void;
  (event: "close-sidebar"): void;
  (event: "toggle-collapse"): void;
}>();

const currentStatusLabel = computed(() => {
  if (props.cacheClearing) {
    return "清理缓存中";
  }
  if (props.status === "loading") {
    return "生成中";
  }
  if (props.status === "error") {
    return "失败";
  }
  if (props.report) {
    return getStatusLabel(props.report.status);
  }
  return "未开始";
});

function handleSelect(taskId: string): void {
  if (props.busy) {
    return;
  }
  emit("select-report", taskId);
}
</script>

<template>
  <div class="sidebar-nav" :class="{ 'sidebar-nav--collapsed': collapsed }">
    <template v-if="collapsed">
      <section class="sidebar-section sidebar-brand sidebar-brand--collapsed">
        <p class="sidebar-brand__title">赛诺</p>
        <p class="sidebar-brand__subtitle">SW</p>
      </section>

      <section class="sidebar-section sidebar-compact-actions">
        <button class="secondary-button sidebar-compact-button" type="button" :disabled="busy" @click="emit('toggle-collapse')">
          展开
        </button>
        <button class="secondary-button sidebar-compact-button" type="button" :disabled="busy" @click="emit('new-analysis')">
          新建
        </button>
        <button class="secondary-button sidebar-compact-button" type="button" :disabled="busy" @click="emit('fill-example')">
          示例
        </button>
        <button class="secondary-button sidebar-compact-button" type="button" :disabled="busy || !history.length" @click="emit('clear-history')">
          清空
        </button>
      </section>
    </template>

    <template v-else>
      <section class="sidebar-section sidebar-brand">
        <p class="sidebar-brand__title">企业体检报告</p>
        <p class="sidebar-brand__subtitle">Saino Workspace</p>
      </section>

      <section class="sidebar-section">
        <div class="sidebar-actions">
          <button class="primary-button" type="button" :disabled="busy" @click="emit('new-analysis')">新建分析</button>
          <button class="secondary-button" type="button" :disabled="busy" @click="emit('fill-example')">填充示例</button>
          <button class="secondary-button" type="button" :disabled="busy" @click="emit('clear-inputs')">清空输入</button>
        </div>
      </section>

      <section class="sidebar-section">
        <div class="sidebar-heading">
          <span>当前任务</span>
          <span class="status-pill status-pill--neutral">{{ currentStatusLabel }}</span>
        </div>
        <dl class="snapshot-list">
          <div>
            <dt>公司</dt>
            <dd>{{ form.companyCode || "未填写" }}</dd>
          </div>
          <div>
            <dt>问题</dt>
            <dd>{{ form.query ? summarizeText(form.query, 72) : "等待输入分析问题" }}</dd>
          </div>
        </dl>
      </section>

      <section class="sidebar-section sidebar-section--grow">
        <div class="sidebar-heading">
          <span>最近分析</span>
          <div class="sidebar-heading__actions">
            <span class="sidebar-counter">{{ history.length }}</span>
            <button class="text-button" type="button" :disabled="busy || !history.length" @click="emit('clear-history')">清空</button>
          </div>
        </div>
        <div v-if="history.length" class="history-list">
          <button
            v-for="item in history"
            :key="item.task_id"
            class="history-card"
            type="button"
            :disabled="busy"
            :class="{ 'history-card--active': report?.task_id === item.task_id }"
            @click="handleSelect(item.task_id)"
          >
            <strong>{{ item.report_title || item.company_code }}</strong>
            <span>{{ summarizeText(item.query, 54) }}</span>
            <small>{{ formatDateTime(item.created_at) }}</small>
          </button>
        </div>
        <p v-else class="sidebar-empty">最近的分析记录会显示在这里。</p>
      </section>

      <details class="sidebar-section sidebar-section--muted sidebar-details">
        <summary class="sidebar-heading sidebar-heading--summary">
          <span>系统状态 / 调试信息</span>
          <div class="sidebar-heading__actions">
            <button class="text-button text-button--desktop" type="button" :disabled="busy" @click.prevent="emit('toggle-collapse')">
              收起
            </button>
            <button class="text-button text-button--mobile" type="button" :disabled="busy" @click.prevent="emit('close-sidebar')">
              关闭
            </button>
          </div>
        </summary>
        <dl class="system-list">
          <div>
            <dt>模型</dt>
            <dd>{{ health?.model_name || "未配置" }}</dd>
          </div>
          <div>
            <dt>调用链路</dt>
            <dd>{{ getModeLabel(health) }}</dd>
          </div>
          <div>
            <dt>配置状态</dt>
            <dd>{{ health?.llm_ready ? "就绪" : "待配置" }}</dd>
          </div>
          <div>
            <dt>接口</dt>
            <dd>{{ health ? "已连接" : "未连接" }}</dd>
          </div>
          <div>
            <dt>PDF</dt>
            <dd>可导出</dd>
          </div>
          <div>
            <dt>Skill</dt>
            <dd>{{ Object.keys(skillCatalog).length }} 个已注册</dd>
          </div>
          <div>
            <dt>检索深度</dt>
            <dd>{{ form.topK }}</dd>
          </div>
        </dl>
      </details>
    </template>
  </div>
</template>
