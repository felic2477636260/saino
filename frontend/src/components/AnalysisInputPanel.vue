<script setup lang="ts">
import { computed, ref } from "vue";

import type { PromptTemplate, UploadCapabilityResponse, UploadedDocumentItem } from "@/types/api";
import type { UploadMaterialType } from "@/types/workspace";

const props = defineProps<{
  promptTemplates: PromptTemplate[];
  activeTemplateId: string;
  currentTemplate: PromptTemplate | null;
  materialType: UploadMaterialType;
  companyCode: string;
  query: string;
  preferenceNote: string;
  topK: number;
  uploadedDocuments: UploadedDocumentItem[];
  uploadCapabilities: UploadCapabilityResponse;
  uploadQueue: Array<{
    id: string;
    name: string;
    status: "uploading" | "success" | "error";
    detail?: string;
  }>;
  disabled: boolean;
  uploading: boolean;
  canUpload: boolean;
  submitting: boolean;
  cacheClearing: boolean;
  canSubmit: boolean;
  noticeMessage?: string;
  noticeTone?: "success" | "info";
}>();

const emit = defineEmits<{
  (event: "update:material-type", value: UploadMaterialType): void;
  (event: "update:company-code", value: string): void;
  (event: "update:query", value: string): void;
  (event: "update:preference-note", value: string): void;
  (event: "update:top-k", value: number): void;
  (event: "upload-files", value: File[]): void;
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

const fileInputRef = ref<HTMLInputElement | null>(null);
const materialTypeOptions: Array<{ value: UploadMaterialType; label: string; description: string }> = [
  { value: "company", label: "公司资料", description: "年报、季报、公告、产品资料等" },
  { value: "research", label: "研究资料", description: "券商研报、行业跟踪、专题分析等" },
  { value: "industry", label: "行业资料", description: "政策、竞品、行业趋势和外部环境材料" },
];

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
const uploadQueueTitle = computed(() => {
  if (props.uploading) {
    return `正在上传 ${props.uploadQueue.length} 个文件`;
  }
  if (props.uploadQueue.some((item) => item.status === "error")) {
    return "最近一次上传结果";
  }
  if (props.uploadQueue.some((item) => item.status === "success")) {
    return "已完成上传";
  }
  return "上传状态";
});
const supportedFileTypes = computed(() => props.uploadCapabilities.allowed_file_types);
const acceptExtensions = computed(() => props.uploadCapabilities.accept_extensions.join(","));

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

function openFilePicker(): void {
  if (!props.canUpload) {
    return;
  }
  fileInputRef.value?.click();
}

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (files.length) {
    emit("upload-files", files);
  }
  input.value = "";
}

function formatReportType(reportType: string): string {
  const labels: Record<string, string> = {
    annual_report: "公司资料",
    research_report: "研究资料",
    industry_report: "行业资料",
  };
  return labels[reportType] || reportType;
}

function uploadQueueTone(status: "uploading" | "success" | "error"): string {
  if (status === "success") {
    return "good";
  }
  if (status === "error") {
    return "risk";
  }
  return "neutral";
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

    <section class="upload-card">
      <div class="upload-card__header">
        <div>
          <p class="eyebrow">资料上传</p>
          <h3>上传用于判断的原始资料</h3>
          <p>上传后会自动归档并纳入当前公司的分析资料库，后续生成报告时会作为证据依据。</p>
        </div>
        <div class="upload-card__types">
          <span>当前支持：</span>
          <strong>{{ supportedFileTypes.join(" / ") }}</strong>
        </div>
      </div>

      <div class="upload-card__controls">
        <label class="upload-field">
          <span>资料分类</span>
          <select
            :value="materialType"
            :disabled="disabled || uploading"
            @change="emit('update:material-type', ($event.target as HTMLSelectElement).value as UploadMaterialType)"
          >
            <option v-for="option in materialTypeOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <small>{{ materialTypeOptions.find((item) => item.value === materialType)?.description }}</small>
        </label>

        <div class="upload-actions">
          <button class="secondary-button" type="button" :disabled="!canUpload" @click="openFilePicker">
            {{ uploading ? "上传中..." : "选择并上传文件" }}
          </button>
          <small v-if="!companyCode.trim()">请先填写公司代码，再上传资料。</small>
          <small v-else>上传完成后，文件会出现在下方资料列表中，并自动参与后续分析。</small>
          <input
            ref="fileInputRef"
            class="upload-input"
            type="file"
            multiple
            :accept="acceptExtensions"
            @change="handleFileChange"
          />
        </div>
      </div>

      <div v-if="uploadQueue.length" class="upload-progress">
        <div class="upload-progress__header">
          <strong>{{ uploadQueueTitle }}</strong>
          <span v-if="uploading">系统正在处理，请稍候</span>
        </div>
        <div v-if="uploading" class="upload-progress__bar">
          <span />
        </div>
        <div class="upload-progress__list">
          <article v-for="item in uploadQueue" :key="item.id" class="upload-progress__item">
            <div class="upload-progress__item-top">
              <strong>{{ item.name }}</strong>
              <span class="status-pill" :class="`status-pill--${uploadQueueTone(item.status)}`">
                {{ item.status === "uploading" ? "上传中" : item.status === "success" ? "已上传" : "失败" }}
              </span>
            </div>
            <small v-if="item.detail">{{ item.detail }}</small>
          </article>
        </div>
      </div>

      <div class="upload-card__hint">
        <span>参考当前游戏数据集，建议优先上传公司年报、季度资料、行业研报和专题跟踪材料。</span>
      </div>

      <div class="upload-list">
        <div class="sidebar-heading">
          <span>当前公司已接入资料</span>
          <span class="sidebar-counter">{{ uploadedDocuments.length }}</span>
        </div>

        <div v-if="uploadedDocuments.length" class="upload-list__items">
          <article v-for="item in uploadedDocuments" :key="item.doc_id" class="upload-doc-card">
            <div class="upload-doc-card__top">
              <strong>{{ item.filename }}</strong>
              <span class="template-badge template-badge--soft">{{ formatReportType(item.report_type) }}</span>
            </div>
            <p>{{ item.title || item.filename }}</p>
            <small>{{ item.total_pages }} 页{{ item.created_at ? ` · ${item.created_at}` : "" }}</small>
          </article>
        </div>

        <p v-else class="empty-note">还没有接入资料。上传成功后，这些文件会自动进入当前公司的资料列表。</p>
      </div>
    </section>

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
