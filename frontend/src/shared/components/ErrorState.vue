<template>
  <section class="state-panel state-error" role="alert">
    <h2>{{ title }}</h2>
    <p>{{ message }}</p>
    <button v-if="retryable" type="button" @click="$emit('retry')">重试身份验证</button>
    <slot />
  </section>
</template>
<script setup lang="ts">
withDefaults(defineProps<{ title?: string; message: string; retryable?: boolean }>(), {
  title: '暂时无法加载', retryable: false,
})
defineEmits<{ retry: [] }>()
</script>
