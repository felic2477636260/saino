<script setup lang="ts">
import { computed } from "vue";

import { buildSkillGroups, getTechnicalDiagnostics } from "@/lib/report";
import type { ReportDetailResponse, SkillCatalog } from "@/types/api";

const props = defineProps<{
  report: ReportDetailResponse;
  skillCatalog: SkillCatalog;
}>();

const groups = computed(() => buildSkillGroups(props.report, props.skillCatalog));
const diagnostics = computed(() => getTechnicalDiagnostics(props.report));
</script>

<template>
  <details class="surface-card section-card technical-details">
    <summary class="technical-details__summary">
      <div>
        <p class="eyebrow">技术详情</p>
        <h3>研究过程 / 调试信息</h3>
      </div>
      <span class="status-pill status-pill--neutral">默认收起</span>
    </summary>

    <div class="technical-details__body">
      <dl v-if="diagnostics.length" class="technical-details__grid">
        <div v-for="item in diagnostics" :key="item.label">
          <dt>{{ item.label }}</dt>
          <dd>{{ item.value }}</dd>
        </div>
      </dl>

      <div class="skill-groups">
        <section v-for="group in groups" :key="group.title" class="skill-group">
          <header>
            <h4>{{ group.title }}</h4>
          </header>
          <div v-if="group.items.length" class="skill-list">
            <article v-for="item in group.items" :key="item.key" class="skill-card">
              <div class="skill-card__top">
                <strong>{{ item.label }}</strong>
                <span class="status-pill status-pill--neutral">{{ item.typeLabel }}</span>
              </div>
              <p>{{ item.description }}</p>
              <small>{{ item.summary }}</small>
              <footer v-if="item.findingsCount || item.recommendationsCount">
                发现 {{ item.findingsCount }} 项 · 建议 {{ item.recommendationsCount }} 项
              </footer>
            </article>
          </div>
          <p v-else class="empty-note">{{ group.emptyText }}</p>
        </section>
      </div>
    </div>
  </details>
</template>
