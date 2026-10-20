import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import type { Role } from '../shared/api/types'
import { roleHome } from '../shared/navigation'
import { featureRoutes } from '../features/routes'
import type { AuthStore } from '../features/auth/store'
import LoginPage from '../features/auth/LoginPage.vue'
import FeaturePage from '../shared/components/FeaturePage.vue'
import StatusPage from './StatusPage.vue'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    roles: Role[]
    title?: string
    description?: string
  }
}

export function createAppRouter(
  auth: AuthStore,
  history: RouterHistory = createWebHistory(),
  hasFatalError: () => boolean = () => false,
) {
  const router = createRouter({
    history,
    routes: [
      { path: '/', name: 'home', component: FeaturePage, meta: { roles: [] } },
      { path: '/login', name: 'login', component: LoginPage, meta: { public: true, roles: [] } },
      ...featureRoutes.map(({ path, title, description, roles }) => ({
        path, component: FeaturePage, meta: { title, description, roles },
      })),
      { path: '/forbidden', name: 'forbidden', component: StatusPage, props: { kind: 'forbidden' }, meta: { roles: [] } },
      { path: '/service-unavailable', name: 'unavailable', component: StatusPage, props: { kind: 'unavailable' }, meta: { public: true, roles: [] } },
      { path: '/:pathMatch(.*)*', name: 'not-found', component: StatusPage, props: { kind: 'not-found' }, meta: { public: true, roles: [] } },
    ],
  })
  router.beforeEach(async (to) => {
    await auth.restoreSession()
    if (auth.restoreError && to.name !== 'unavailable') return { name: 'unavailable' }
    if (hasFatalError() && to.name !== 'unavailable') return { name: 'unavailable' }
    if (to.meta.public) {
      if (to.name === 'login' && auth.actor) return roleHome[auth.actor.role]
      return true
    }
    if (!auth.actor) return { name: 'login' }
    if (to.name === 'home') return roleHome[auth.actor.role]
    if (to.meta.roles.length && !to.meta.roles.includes(auth.actor.role)) return { name: 'forbidden' }
    return true
  })
  return router
}
