<script setup lang="ts">
import { computed } from "vue";

import { formatDateTime, getExecutiveSummary, getRiskTone, getScoreBreakdown, getSummaryMetrics } from "@/lib/report";
import type { ReportDetailResponse } from "@/types/api";

const props = defineProps<{
  report: ReportDetailResponse;
}>();

const executiveSummary = computed(() => getExecutiveSummary(props.report));
const riskTone = computed(() => `status-pill--${getRiskTone(props.report.risk_level)}`);
const summaryMetrics = computed(() => getSummaryMetrics(props.report));
const scoreBreakdown = computed(() => getScoreBreakdown(props.report));
const dimensionMetrics = computed(() => summaryMetrics.value.filter((item) => item.label !== "总分" && item.label !== "风险等级"));
</script>

<template>
  <section class="surface-card section-card">
    <div class="section-heading">
      <div>
        <p class="eyebrow">执行摘要</p>
        <h3>先看结论</h3>
      </div>
      <span class="status-pill" :class="riskTone">{{ report.risk_level }}</span>
    </div>

    <div class="executive-summary-card">
      <p>{{ executiveSummary }}</p>
      <dl class="executive-summary-card__meta">
        <div v-for="card in dimensionMetrics" :key="card.label">
          <dt>{{ card.label }}</dt>
          <dd>{{ card.value }}</dd>
        </div>
        <div>
          <dt>生成时间</dt>
          <dd>{{ formatDateTime(report.created_at) }}</dd>
        </div>
      </dl>
    </div>

    <div v-if="scoreBreakdown" class="score-breakdown">
      <div class="section-heading">
        <div>
          <p class="eyebrow">评分拆解</p>
          <h3>经营评分快照</h3>
        </div>
      </div>

      <div class="score-breakdown__grid">
        <article
          v-for="dimension in scoreBreakdown.dimensions"
          :key="dimension.dimension_key"
          class="score-breakdown__card"
        >
          <div class="score-breakdown__top">
            <strong>{{ dimension.dimension_label }}</strong>
            <span>{{ dimension.score }} / {{ dimension.max_score }}</span>
          </div>
          <p>{{ dimension.summary }}</p>
          <small v-if="dimension.negative_factors.length">
            主要扣分：{{ dimension.negative_factors.slice(0, 2).join("；") }}
          </small>
          <small v-else-if="dimension.positive_factors.length">
            主要支撑：{{ dimension.positive_factors.slice(0, 2).join("；") }}
          </small>
        </article>
      </div>

      <div v-if="scoreBreakdown.top_deductions.length" class="score-breakdown__deductions">
        <strong>三个最主要扣分原因</strong>
        <ul>
          <li v-for="item in scoreBreakdown.top_deductions.slice(0, 3)" :key="item">{{ item }}</li>
        </ul>
      </div>
    </div>
  </section>
</template>
