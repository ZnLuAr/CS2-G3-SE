<template>
  <div class="status-page">
    <ErrorState v-if="kind === 'forbidden'" title="无权访问" message="当前账号无法进入此页面，请从菜单选择可用功能。" />
    <ErrorState
      v-else-if="kind === 'unavailable'"
      title="服务暂时不可用"
      :message="auth.restoreError || fatalMessage || '请稍后重试，或联系维护人员。'"
      :retryable="Boolean(auth.restoreError)"
      @retry="retry"
    />
    <ErrorState v-else title="页面不存在" message="请检查地址，或返回首页继续。" />
    <RouterLink v-if="!auth.restoreError" class="text-link" to="/" @click="clearFatalError">返回首页</RouterLink>
  </div>
</template>
<script setup lang="ts">
import { useAppContext } from './context'
import { useRouter } from 'vue-router'
import ErrorState from '../shared/components/ErrorState.vue'
defineProps<{ kind: 'forbidden' | 'unavailable' | 'not-found' }>()
const { auth, fatalMessage } = useAppContext()
const router = useRouter()

async function retry(): Promise<void> {
  fatalMessage.value = null
  await auth.retryRestoreSession()
  if (auth.actor) await router.replace('/')
}

function clearFatalError(): void {
  fatalMessage.value = null
}
</script>
