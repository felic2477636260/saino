<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

const steps = [
  "正在分析财报与研报信息，请稍候",
  "正在提取关键证据与页码",
  "正在生成企业体检报告",
];

const activeStep = ref(0);
let timer: number | null = null;

onMounted(() => {
  timer = window.setInterval(() => {
    activeStep.value = (activeStep.value + 1) % steps.length;
  }, 1600);
});

onUnmounted(() => {
  if (timer !== null) {
    window.clearInterval(timer);
  }
});
</script>

<template>
  <section class="loading-state surface-card fade-in">
    <div class="loading-state__skeleton">
      <span />
      <span />
      <span />
    </div>
    <div class="loading-state__steps">
      <p class="eyebrow">报告生成中</p>
      <ul>
        <li v-for="(step, index) in steps" :key="step" :class="{ 'is-active': index === activeStep }">
          {{ step }}
        </li>
      </ul>
    </div>
  </section>
</template>
