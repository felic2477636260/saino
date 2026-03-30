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
const totalSkills = computed(() => groups.value.reduce((count, group) => count + group.items.length, 0));
const genericSkills = computed(() => groups.value[0]?.items.length ?? 0);
const customSkills = computed(() => groups.value[1]?.items.length ?? 0);
</script>

<template>
  <section class="surface-card workbench-panel fade-in">
    <header class="workbench-panel__header">
      <div>
        <p class="eyebrow">分析工作台</p>
        <h3>本次分析动用了哪些 Skills</h3>
        <p class="workbench-panel__subtitle">
          这里展示的是本次分析过程中的工作量与能力分工，只作为前端工作台说明，不属于最终输出报告正文。
        </p>
      </div>

      <div class="workbench-panel__summary">
        <article class="workbench-metric">
          <span>已触发技能</span>
          <strong>{{ totalSkills }}</strong>
        </article>
        <article class="workbench-metric">
          <span>通用技能</span>
          <strong>{{ genericSkills }}</strong>
        </article>
        <article class="workbench-metric">
          <span>行业/定制技能</span>
          <strong>{{ customSkills }}</strong>
        </article>
      </div>
    </header>

    <dl v-if="diagnostics.length" class="workbench-panel__diagnostics">
      <div v-for="item in diagnostics" :key="item.label">
        <dt>{{ item.label }}</dt>
        <dd>{{ item.value }}</dd>
      </div>
    </dl>

    <div class="workbench-panel__groups">
      <section v-for="group in groups" :key="group.title" class="workbench-group">
        <header class="workbench-group__header">
          <h4>{{ group.title }}</h4>
          <span class="status-pill status-pill--neutral">{{ group.items.length }} 个</span>
        </header>

        <div v-if="group.items.length" class="skill-list">
          <article v-for="item in group.items" :key="item.key" class="skill-card skill-card--workbench">
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
  </section>
</template>
