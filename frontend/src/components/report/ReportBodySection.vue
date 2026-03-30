<script setup lang="ts">
import { computed } from "vue";

import { getOrderedReportSections } from "@/lib/report";
import type { ReportDetailResponse } from "@/types/api";

const props = defineProps<{
  report: ReportDetailResponse;
}>();

const sections = computed(() =>
  getOrderedReportSections(props.report).filter((item) => {
    const key = item.key.trim();
    const label = item.label.trim();
    return key !== "executive_summary" && key !== "conclusion" && label !== "执行摘要" && label !== "鎵ц鎽樿";
  }),
);
</script>

<template>
  <article class="report-body surface-card fade-in">
    <header class="report-body__header">
      <p class="eyebrow">报告正文</p>
      <h3>把结论讲透的 3-4 个关键议题</h3>
      <p>正文只保留对当前判断最关键的模块，每个模块都按“证据、信号、含义、结论”展开，不再重复执行摘要。</p>
    </header>

    <nav v-if="sections.length" class="report-body__toc">
      <a v-for="item in sections" :key="item.key" :href="`#section-${item.key}`">
        {{ item.label }}
      </a>
    </nav>

    <section v-for="item in sections" :id="`section-${item.key}`" :key="item.key" class="report-body__section">
      <p v-if="item.expertRole" class="eyebrow">{{ item.expertRole }}</p>
      <h4>{{ item.label }}</h4>
      <p v-if="item.summary" class="report-body__summary">
        {{ item.summary }}
      </p>
      <p v-for="paragraph in item.paragraphs" :key="paragraph">
        {{ paragraph }}
      </p>
      <ul v-if="item.pendingChecks.length" class="report-body__checks">
        <li v-for="check in item.pendingChecks" :key="check">
          {{ check }}
        </li>
      </ul>
    </section>
  </article>
</template>
