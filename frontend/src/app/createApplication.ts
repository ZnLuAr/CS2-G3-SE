import { createApp, ref } from 'vue'
import { createPinia } from 'pinia'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import type { RouterHistory } from 'vue-router'
import App from './App.vue'
import { appContextKey } from './context'
import { createAppRouter } from './router'
import { createApiClient } from '../shared/api/client'
import { createAuthApi } from '../features/auth/api'
import { createAuthStore, type AuthStore } from '../features/auth/store'

/** 每个应用实例拥有独立身份、HTTP 请求生命周期与查询缓存。 */
export function createApplication(options: { history?: RouterHistory; storage?: Storage; baseURL?: string } = {}) {
  const pinia = createPinia()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30_000 } } })
  const fatalMessage = ref<string | null>(null)
  let auth: AuthStore | undefined
  let router: ReturnType<typeof createAppRouter> | undefined
  const client = createApiClient({
    baseURL: (options.baseURL ?? import.meta.env.VITE_API_BASE_URL)?.trim() || '/api',
    getAccessToken: () => auth?.accessToken ?? null,
    onError(error) {
      if (error.payload.action === 'login') {
        auth?.clearSession()
        if (router?.currentRoute.value.name !== 'login') void router?.replace({ name: 'login' })
      } else if (error.payload.action === 'exit') {
        fatalMessage.value = error.message
        void queryClient.cancelQueries()
        client.cancelRequests()
        void router?.replace({ name: 'unavailable' })
      }
    },
  })
  auth = createAuthStore({
    api: createAuthApi(client),
    storage: options.storage ?? window.sessionStorage,
    clearPrivateState() {
      client.cancelRequests()
      void queryClient.cancelQueries()
      queryClient.clear()
    },
  })(pinia)
  router = createAppRouter(auth, options.history, () => fatalMessage.value !== null)
  const app = createApp(App)
  app.use(pinia)
  app.use(VueQueryPlugin, { queryClient })
  app.use(router)
  app.provide(appContextKey, { auth, fatalMessage })
  return { app, auth, router, queryClient, client, fatalMessage }
}
