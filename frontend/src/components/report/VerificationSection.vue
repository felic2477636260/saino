<script setup lang="ts">
import type { VerificationNote } from "@/types/api";

defineProps<{
  verificationNotes: VerificationNote[];
}>();
</script>

<template>
  <section class="surface-card section-card">
    <div class="section-heading">
      <div>
        <p class="eyebrow">核验提示</p>
        <h3>证据边界与冲突</h3>
      </div>
      <span class="sidebar-counter">{{ verificationNotes.length }}</span>
    </div>

    <ul v-if="verificationNotes.length" class="finding-list">
      <li v-for="note in verificationNotes" :key="`${note.title}-${note.detail}`">
        <strong>{{ note.title }}</strong>
        <p>{{ note.detail }}</p>
      </li>
    </ul>
    <p v-else class="empty-note">当前未发现明显证据缺口或冲突。</p>
  </section>
</template>
