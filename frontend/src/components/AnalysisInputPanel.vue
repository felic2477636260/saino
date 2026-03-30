<script setup lang="ts">
const props = defineProps<{
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
  (event: "submit"): void;
  (event: "fill-example"): void;
  (event: "clear"): void;
  (event: "clear-cache"): void;
}>();

function handleShortcut(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && props.canSubmit && !props.disabled) {
    event.preventDefault();
    emit("submit");
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
        placeholder="描述你希望系统重点分析的核心问题，例如经营质量、盈利能力、现金流、增长持续性或行业竞争。"
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
        placeholder="可以直接写自然语言，例如：更关心财务风险；重点看现金流和偿债能力；先给结论和评分；报告简洁一点；偏投资研究风格；重点看游戏产品生命周期和出海能力。"
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
          示例
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
