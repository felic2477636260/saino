<script setup lang="ts">
import { getToneLabel } from "@/lib/report";
import type { ReportJudgment } from "@/types/api";

defineProps<{
  judgments: ReportJudgment[];
}>();
</script>

<template>
  <section class="surface-card section-card">
    <div class="section-heading">
      <div>
        <p class="eyebrow">核心结论</p>
        <h3>最重要的判断</h3>
      </div>
    </div>

    <div v-if="judgments.length" class="judgment-list">
      <article v-for="judgment in judgments" :key="`${judgment.title}-${judgment.verdict}`" class="judgment-card">
        <div class="judgment-card__header">
          <div>
            <strong>{{ judgment.title }}</strong>
            <p>{{ judgment.verdict }}</p>
          </div>
          <span class="status-pill" :class="`status-pill--${judgment.tone}`">{{ getToneLabel(judgment.tone) }}</span>
        </div>
        <p v-if="judgment.explanation" class="judgment-card__explanation">{{ judgment.explanation }}</p>
        <div v-if="judgment.evidence_anchors.length" class="judgment-card__anchors">
          <small v-for="anchor in judgment.evidence_anchors" :key="anchor">{{ anchor }}</small>
        </div>
      </article>
    </div>
    <p v-else class="empty-note">当前没有额外结论。</p>
  </section>
</template>
