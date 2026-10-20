<template>
  <div>
    <header class="page-heading"><h1>{{ route.meta.title }}</h1><p>{{ route.meta.description }}</p></header>
    <EmptyState title="功能准备中" message="此功能开放后，即可在这里办理。" />
  </div>
</template>
<script setup lang="ts">
import { useRoute } from 'vue-router'
import EmptyState from './EmptyState.vue'
const route = useRoute()
</script>
