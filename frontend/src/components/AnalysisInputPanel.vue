<script setup lang="ts">
import { computed } from "vue";

import type { PromptTemplate } from "@/types/api";

const props = defineProps<{
  promptTemplates: PromptTemplate[];
  activeTemplateId: string;
  currentTemplate: PromptTemplate | null;
  companyCode: string;
  query: string;
  preferenceNote: string;
  topK: number;
  disabled: boolean;
  submitting: boolean;
  cacheClearing: boolean;
  canSubmit: boolean;
  noticeMessage?: string;
  noticeTone?: "success" | "info";
}>();

const emit = defineEmits<{
  (event: "update:company-code", value: string): void;
  (event: "update:query", value: string): void;
  (event: "update:preference-note", value: string): void;
  (event: "update:top-k", value: number): void;
  (event: "select-template", value: string): void;
  (event: "apply-template"): void;
  (event: "submit"): void;
  (event: "fill-example"): void;
  (event: "clear"): void;
  (event: "clear-cache"): void;
}>();

interface ModuleGroupMeta {
  key: string;
  label: string;
  description: string;
}

const moduleGroups = computed<ModuleGroupMeta[]>(() => {
  const hasFeatured = props.promptTemplates.some((item) => item.module_group === "featured");
  const groups: ModuleGroupMeta[] = [];

  if (hasFeatured) {
    groups.push({
      key: "featured",
      label: "专属行业",
      description: "已内置专属板块或专属增强能力的行业",
    });
  }

  groups.push({
    key: "custom",
    label: "自定义模块",
    description: "其他行业模板和通用分析入口统一归入这里",
  });

  return groups;
});

const activeModuleKey = computed(() => props.currentTemplate?.module_group || moduleGroups.value[0]?.key || "custom");
const visibleTemplates = computed(() => props.promptTemplates.filter((item) => item.module_group === activeModuleKey.value));
const activeModuleMeta = computed(
  () => moduleGroups.value.find((item) => item.key === activeModuleKey.value) || moduleGroups.value[0] || null,
);

function handleShortcut(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && props.canSubmit && !props.disabled) {
    event.preventDefault();
    emit("submit");
  }
}

function selectModule(moduleKey: string): void {
  const firstTemplate = props.promptTemplates.find((item) => item.module_group === moduleKey);
  if (firstTemplate) {
    emit("select-template", firstTemplate.template_id);
  }
}
</script>

<template>
  <section class="input-panel surface-card fade-in">
    <div class="input-panel__header">
      <div>
        <p class="eyebrow">分析输入</p>
        <h2>围绕企业公开信息发起一次正式分析</h2>
      </div>
      <p class="input-panel__shortcut">Ctrl / Cmd + Enter 提交</p>
    </div>

    <div class="template-browser">
      <div class="template-browser__modules" role="tablist" aria-label="模板模块">
        <button
          v-for="group in moduleGroups"
          :key="group.key"
          class="module-chip"
          :class="{ 'module-chip--active': group.key === activeModuleKey }"
          type="button"
          :disabled="disabled"
          @click="selectModule(group.key)"
        >
          <strong>{{ group.label }}</strong>
          <span>{{ group.description }}</span>
        </button>
      </div>

      <div class="template-browser__subnav">
        <div>
          <p class="eyebrow">{{ activeModuleMeta?.label || "模板导航" }}</p>
          <p class="template-browser__summary">{{ activeModuleMeta?.description }}</p>
        </div>

        <div class="template-browser__tabs" role="tablist" aria-label="行业模板">
          <button
            v-for="template in visibleTemplates"
            :key="template.template_id"
            class="template-chip"
            :class="{ 'template-chip--active': template.template_id === activeTemplateId }"
            type="button"
            :disabled="disabled"
            @click="emit('select-template', template.template_id)"
          >
            {{ template.industry_label }}
          </button>
        </div>
      </div>

      <article v-if="currentTemplate" class="template-card">
        <div class="template-card__header">
          <div>
            <div class="template-card__badges">
              <span class="template-badge">{{ currentTemplate.capability_label }}</span>
              <span class="template-badge template-badge--soft">{{ currentTemplate.industry_label }}</span>
            </div>
            <h3>{{ currentTemplate.title }}</h3>
            <p>{{ currentTemplate.description }}</p>
          </div>

          <button class="secondary-button" type="button" :disabled="disabled" @click="emit('apply-template')">
            套用当前模板
          </button>
        </div>

        <div class="template-card__columns">
          <section class="template-card__column">
            <span>完整提示词示例</span>
            <div class="template-preview">{{ currentTemplate.query_template }}</div>
          </section>

          <section class="template-card__column">
            <span>补充偏好示例</span>
            <div class="template-preview">
              {{ currentTemplate.preference_template || "可留空，自行补充风格和重点。" }}
            </div>
          </section>
        </div>

        <div class="template-card__columns">
          <section class="template-card__column">
            <span>写提示词时建议覆盖</span>
            <ul class="template-list">
              <li v-for="item in currentTemplate.guidance" :key="item">{{ item }}</li>
            </ul>
          </section>

          <section class="template-card__column">
            <span>建议先上传的资料</span>
            <ul class="template-list">
              <li v-for="item in currentTemplate.suggested_documents" :key="item">{{ item }}</li>
            </ul>
            <small v-if="currentTemplate.example_company_code">示例公司代码：{{ currentTemplate.example_company_code }}</small>
          </section>
        </div>
      </article>
    </div>

    <p
      v-if="noticeMessage"
      class="notice-banner"
      :class="{
        'notice-banner--success': noticeTone === 'success',
        'notice-banner--info': noticeTone === 'info',
      }"
    >
      {{ noticeMessage }}
    </p>

    <label class="form-field">
      <span>公司代码 / 公司名称</span>
      <input
        :value="companyCode"
        type="text"
        placeholder="输入公司代码或名称"
        :disabled="disabled"
        @input="emit('update:company-code', ($event.target as HTMLInputElement).value)"
      />
    </label>

    <label class="form-field">
      <span>分析问题</span>
      <textarea
        :value="query"
        rows="5"
        placeholder="可参考上方模板，自行修改为你真正想分析的问题。"
        :disabled="disabled"
        @input="emit('update:query', ($event.target as HTMLTextAreaElement).value)"
        @keydown="handleShortcut"
      />
    </label>

    <label class="form-field">
      <span>分析偏好 / 补充说明</span>
      <textarea
        :value="preferenceNote"
        rows="4"
        placeholder="可以补充报告风格、优先级、风险偏好、输出顺序，或说明你更关心哪些经营问题。"
        :disabled="disabled"
        @input="emit('update:preference-note', ($event.target as HTMLTextAreaElement).value)"
      />
      <small>系统会自动理解你的偏好，并调整报告风格、重点、模块顺序和展开深度。</small>
    </label>

    <div class="input-panel__footer">
      <label class="range-field">
        <span>证据条数</span>
        <div class="range-field__control">
          <input
            :value="topK"
            type="range"
            min="4"
            max="12"
            :disabled="disabled"
            @input="emit('update:top-k', Number(($event.target as HTMLInputElement).value))"
          />
          <strong>{{ topK }}</strong>
        </div>
      </label>

      <div class="action-row">
        <button class="primary-button" type="button" :disabled="disabled || !canSubmit" @click="emit('submit')">
          {{ submitting ? "生成中..." : "生成报告" }}
        </button>
        <button class="secondary-button" type="button" :disabled="disabled" @click="emit('fill-example')">
          填充模板
        </button>
        <button class="secondary-button" type="button" :disabled="disabled" @click="emit('clear')">
          清空
        </button>
        <button
          class="secondary-button secondary-button--danger"
          type="button"
          :disabled="disabled"
          @click="emit('clear-cache')"
        >
          {{ cacheClearing ? "清理中..." : "清理系统缓存" }}
        </button>
      </div>
    </div>
  </section>
</template>
