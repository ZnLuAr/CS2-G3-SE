<template>
  <a class="skip-link" href="#main-content">跳转到内容</a>
  <template v-if="route.name === 'login'"><RouterView /></template>
  <div v-else-if="auth.actor" class="workspace">
    <header class="app-header">
      <RouterLink class="brand" to="/">健身房管理</RouterLink>
      <div class="account-area">
        <span>{{ roleLabels[auth.actor.role] }} · 账号 {{ auth.actor.accountId }}</span>
        <button class="button-quiet" type="button" :disabled="loggingOut" @click="logout">退出登录</button>
      </div>
    </header>
    <aside class="app-sidebar">
      <nav aria-label="功能导航">
        <RouterLink v-for="item in navigation" :key="item.path" :to="item.path">{{ item.title }}</RouterLink>
      </nav>
    </aside>
    <main id="main-content" class="workspace-content" tabindex="-1"><RouterView /></main>
  </div>
  <main v-else id="main-content" class="public-content" tabindex="-1"><RouterView /></main>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppContext } from './context'
import { roleLabels } from '../shared/navigation'
import { featureRoutes } from '../features/routes'
import { ApiError } from '../shared/api/errors'

const { auth } = useAppContext()
const route = useRoute()
const router = useRouter()
const loggingOut = ref(false)
const navigation = computed(() => featureRoutes.filter(item =>
  item.navigation !== false && auth.actor && item.roles.includes(auth.actor.role)))

async function logout(): Promise<void> {
  loggingOut.value = true
  let showLogin = true
  try { await auth.logout() } catch (error) {
    showLogin = !(error instanceof ApiError && error.payload.action === 'exit')
  } finally {
    loggingOut.value = false
    if (showLogin) await router.replace({ name: 'login' })
  }
}
</script>
