<script setup lang="ts">
import { computed } from "vue";

import { formatDateTime, getExecutiveSummary, getRiskTone, getStatusLabel, summarizeText } from "@/lib/report";
import type { ReportDetailResponse } from "@/types/api";

const props = defineProps<{
  report: ReportDetailResponse;
  pdfUrl: string;
}>();

const displayTitle = computed(() => {
  const title = props.report.report_title?.trim();
  if (title && title !== "企业体检报告") {
    return title;
  }
  return `${props.report.company_code} 企业体检报告`;
});

const summaryLead = computed(() => summarizeText(getExecutiveSummary(props.report), 120));
const riskClass = computed(() => `status-pill--${getRiskTone(props.report.risk_level)}`);
</script>

<template>
  <header class="report-header surface-card fade-in">
    <div class="report-header__main">
      <p class="eyebrow">最终报告</p>
      <h2>{{ displayTitle }}</h2>
      <p class="report-header__summary">{{ summaryLead }}</p>
    </div>

    <div class="report-header__meta">
      <dl>
        <div>
          <dt>公司</dt>
          <dd>{{ report.company_code }}</dd>
        </div>
        <div>
          <dt>生成时间</dt>
          <dd>{{ formatDateTime(report.created_at) }}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>
            <span class="status-pill" :class="riskClass">{{ report.risk_level }}</span>
            <span class="report-header__status-text">{{ getStatusLabel(report.status) }}</span>
          </dd>
        </div>
      </dl>
      <a class="secondary-button report-header__download" :href="pdfUrl">下载 PDF</a>
    </div>
  </header>
</template>
