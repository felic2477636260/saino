<script setup lang="ts">
import { getToneLabel } from "@/lib/report";
import type { RiskOpportunityItem } from "@/types/api";

defineProps<{
  risks: RiskOpportunityItem[];
  opportunities: RiskOpportunityItem[];
}>();
</script>

<template>
  <section class="surface-card section-card">
    <div class="section-heading">
      <div>
        <p class="eyebrow">核心风险与机会</p>
        <h3>当前最关键的上下行变量</h3>
      </div>
    </div>

    <div class="insight-columns">
      <section class="insight-group">
        <header>
          <h4>主要风险</h4>
        </header>
        <div v-if="risks.length" class="insight-list">
          <article v-for="item in risks" :key="`${item.title}-${item.summary}`" class="insight-card insight-card--risk">
            <div class="insight-card__header">
              <strong>{{ item.title }}</strong>
              <span class="status-pill" :class="`status-pill--${item.tone}`">{{ getToneLabel(item.tone) }}</span>
            </div>
            <p>{{ item.summary }}</p>
            <small v-if="item.basis">依据：{{ item.basis }}</small>
            <small v-if="item.impact">含义：{{ item.impact }}</small>
            <small v-if="item.follow_up">跟踪：{{ item.follow_up }}</small>
          </article>
        </div>
        <p v-else class="empty-note">当前未提炼出明确风险项。</p>
      </section>

      <section class="insight-group">
        <header>
          <h4>主要机会</h4>
        </header>
        <div v-if="opportunities.length" class="insight-list">
          <article
            v-for="item in opportunities"
            :key="`${item.title}-${item.summary}`"
            class="insight-card insight-card--good"
          >
            <div class="insight-card__header">
              <strong>{{ item.title }}</strong>
              <span class="status-pill" :class="`status-pill--${item.tone}`">{{ getToneLabel(item.tone) }}</span>
            </div>
            <p>{{ item.summary }}</p>
            <small v-if="item.basis">依据：{{ item.basis }}</small>
            <small v-if="item.impact">含义：{{ item.impact }}</small>
            <small v-if="item.follow_up">跟踪：{{ item.follow_up }}</small>
          </article>
        </div>
        <p v-else class="empty-note">当前未提炼出明确机会项。</p>
      </section>
    </div>
  </section>
</template>
