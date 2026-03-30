<script setup lang="ts">
import type { KeyEvidenceDigest } from "@/types/api";

defineProps<{
  evidence: KeyEvidenceDigest[];
}>();
</script>

<template>
  <section class="surface-card section-card">
    <div class="section-heading">
      <div>
        <p class="eyebrow">关键证据</p>
        <h3>支撑结论的来源</h3>
      </div>
      <span class="sidebar-counter">{{ evidence.length }}</span>
    </div>

    <div v-if="evidence.length" class="evidence-digest-list">
      <article v-for="item in evidence" :key="`${item.title}-${item.citation}`" class="evidence-digest-card">
        <strong>{{ item.title }}</strong>
        <p>{{ item.summary }}</p>
        <small v-if="item.supports">支持判断：{{ item.supports }}</small>
        <small v-if="item.citation">{{ item.citation }}</small>
        <small v-if="item.evidence.length">
          关联证据数：{{ item.evidence.length }}
        </small>
      </article>
    </div>
    <p v-else class="empty-note">当前没有可展示的关键证据。</p>
  </section>
</template>
