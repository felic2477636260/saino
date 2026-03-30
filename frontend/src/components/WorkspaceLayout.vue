<template>
  <div class="workspace-layout">
    <section class="workspace-layout__intro">
      <slot name="intro" />
    </section>

    <section class="workspace-layout__status">
      <slot name="status" />
    </section>

    <section class="workspace-layout__content">
      <slot name="content" />
    </section>
  </div>
</template>
