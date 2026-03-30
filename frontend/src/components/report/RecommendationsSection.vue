<script setup lang="ts">
import type { RecommendationAction } from "@/types/api";

defineProps<{
  actions: RecommendationAction[];
  recommendations: string[];
}>();
</script>

<template>
  <section class="surface-card section-card">
    <div class="section-heading">
      <div>
        <p class="eyebrow">建议动作</p>
        <h3>下一步怎么确认和推进</h3>
      </div>
    </div>

    <div v-if="actions.length" class="insight-list">
      <article v-for="item in actions" :key="item.action" class="insight-card">
        <strong>{{ item.action }}</strong>
        <p v-if="item.purpose">对应目的：{{ item.purpose }}</p>
        <small v-if="item.focus">重点材料/指标：{{ item.focus }}</small>
        <small v-if="item.importance">为什么重要：{{ item.importance }}</small>
      </article>
    </div>
    <ol v-else-if="recommendations.length" class="recommendation-list">
      <li v-for="recommendation in recommendations" :key="recommendation">
        {{ recommendation }}
      </li>
    </ol>
    <p v-else class="empty-note">当前没有新增建议动作。</p>
  </section>
</template>
