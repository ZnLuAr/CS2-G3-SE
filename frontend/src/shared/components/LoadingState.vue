<template><p class="state-message" role="status" aria-live="polite">{{ message }}</p></template>
<script setup lang="ts">
withDefaults(defineProps<{ message?: string }>(), { message: '正在加载，请稍候…' })
</script>
