<script setup lang="ts">
defineProps<{
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
}>();

defineEmits<{
  (event: "toggle-sidebar"): void;
  (event: "close-sidebar"): void;
}>();
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--sidebar-collapsed': sidebarCollapsed }">
    <button class="mobile-nav-toggle" type="button" @click="$emit('toggle-sidebar')">
      工作台
    </button>

    <div class="shell-backdrop" :class="{ 'shell-backdrop--visible': sidebarOpen }" @click="$emit('close-sidebar')" />

    <aside class="shell-sidebar" :class="{ 'shell-sidebar--open': sidebarOpen, 'shell-sidebar--collapsed': sidebarCollapsed }">
      <slot name="sidebar" />
    </aside>

    <main class="shell-main">
      <slot />
    </main>
  </div>
</template>
