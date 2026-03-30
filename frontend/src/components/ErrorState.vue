<script setup lang="ts">
defineProps<{
  message: string;
  hasRetry: boolean;
}>();

defineEmits<{
  (event: "retry"): void;
}>();
</script>

<template>
  <section class="error-state surface-card fade-in">
    <div>
      <p class="eyebrow">请求未完成</p>
      <h3>当前分析未能顺利返回结果</h3>
      <p class="error-state__message">{{ message }}</p>
    </div>
    <button v-if="hasRetry" class="secondary-button" type="button" @click="$emit('retry')">
      重试
    </button>
  </section>
</template>
