<script setup lang="ts">
import { computed } from "vue";

import { summarizeText } from "@/lib/report";
import type { EvidenceItem } from "@/types/api";

const props = defineProps<{
  item: EvidenceItem;
  index: number;
}>();

const preview = computed(() => summarizeText(props.item.text, 92));
const sectionLabel = computed(() => props.item.section_path || props.item.section_title || "");
</script>

<template>
  <details class="evidence-card" :open="index === 0">
    <summary>
      <div>
        <strong>{{ item.source }}</strong>
        <span>第 {{ item.page_no }} 页</span>
      </div>
      <small v-if="sectionLabel">{{ sectionLabel }}</small>
      <p>{{ preview }}</p>
    </summary>
    <div class="evidence-card__body">
      <p>{{ item.quote || item.text }}</p>
      <small v-if="item.reason">{{ item.reason }}</small>
    </div>
  </details>
</template>
