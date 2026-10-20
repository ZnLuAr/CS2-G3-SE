<template>
  <main class="login-page">
    <section class="login-intro">
      <RouterLink class="brand" to="/">健身房管理</RouterLink>
      <h1>每一次到场，<br />都安排妥当。</h1>
      <p>课程、预约与日常服务，从这里开始。</p>
    </section>
    <section class="login-form-panel" aria-labelledby="login-title">
      <h2 id="login-title">登录账号</h2>
      <p>使用分配给你的账号登录。</p>
      <form @submit.prevent="submit">
        <label for="username">账号</label>
        <input id="username" v-model="username" name="username" autocomplete="username" required minlength="3" maxlength="50" :disabled="pending" />
        <label for="password">密码</label>
        <input id="password" v-model="password" name="password" type="password" autocomplete="current-password" required minlength="6" maxlength="32" :disabled="pending" />
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button type="submit" :disabled="pending">{{ pending ? '正在登录…' : '登录' }}</button>
      </form>
    </section>
  </main>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAppContext } from '../../app/context'
import { roleHome } from '../../shared/navigation'
import { toApiError } from '../../shared/api/errors'
import { validateLogin } from './validation'

const { auth } = useAppContext()
const router = useRouter()
const username = ref('')
const password = ref('')
const pending = ref(false)
const error = ref<string | null>(null)

async function submit(): Promise<void> {
  if (pending.value) return
  error.value = validateLogin({ username: username.value, password: password.value })
  if (error.value) return
  pending.value = true
  try {
    await auth.login({ username: username.value, password: password.value })
    if (auth.actor) await router.replace(roleHome[auth.actor.role])
  } catch (failure) {
    if (!axios.isCancel(failure)) error.value = toApiError(failure).message
  } finally {
    pending.value = false
    password.value = ''
  }
}
</script>
