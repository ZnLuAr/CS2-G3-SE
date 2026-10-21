<template>
  <section class="state-panel" role="status">
    <h2>{{ title }}</h2>
    <p>{{ message }}</p>
    <slot />
  </section>
</template>
<script setup lang="ts">
withDefaults(defineProps<{ title?: string; message?: string }>(), {
  title: '暂无记录', message: '调整筛选条件后重试。',
})
</script>
