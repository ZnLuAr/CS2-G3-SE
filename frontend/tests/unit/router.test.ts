import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import { createAppRouter } from '../../src/app/router'
import { createAuthStore } from '../../src/features/auth/store'
import { featureRoutes } from '../../src/features/routes'
import { roleHome } from '../../src/shared/navigation'
import type { Actor, Role } from '../../src/shared/api/types'

function setup(role?: Role) {
  const actor: Actor = { accountId: '1', role: role ?? 'member', memberId: role === 'member' ? '2' : null, coachId: role === 'coach' ? '3' : null }
  const auth = createAuthStore({
    storage: sessionStorage,
    clearPrivateState: vi.fn(),
    api: {
      login: vi.fn().mockResolvedValue({ actor, accessToken: 'token', expiresAt: '2099-01-01T00:00:00Z', tokenType: 'bearer' }),
      me: vi.fn().mockResolvedValue(actor), logout: vi.fn(),
    },
  })(createPinia())
  return { auth, router: createAppRouter(auth, createMemoryHistory()) }
}

beforeEach(() => sessionStorage.clear())
describe('角色路由（模拟身份）', () => {
  it('未登录访问受保护页面返回登录页', async () => {
    const { router } = setup()
    await router.push('/admin/accounts')
    expect(router.currentRoute.value.name).toBe('login')
  })

  it.each(['member', 'coach', 'receptionist', 'admin'] as const)('%s 登录后进入自己的首页', async role => {
    const { auth, router } = setup(role)
    await auth.login({ username: 'test_user', password: 'Pass_123' })
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe(roleHome[role])
  })

  it('会员进入管理页面显示无权访问', async () => {
    const { auth, router } = setup('member')
    await auth.login({ username: 'member', password: 'Pass_123' })
    await router.push('/admin/accounts')
    expect(router.currentRoute.value.name).toBe('forbidden')
  })

  it('管理员可以进入前台业务区', async () => {
    const { auth, router } = setup('admin')
    await auth.login({ username: 'admin', password: 'Pass_123' })
    await router.push('/front/sales')
    expect(router.currentRoute.value.path).toBe('/front/sales')
  })

  it.each(['/profile', '/orders', '/orders/17'])('会员可以进入本人业务入口%s', async path => {
    const { auth, router } = setup('member')
    await auth.login({ username: 'member', password: 'Pass_123' })
    await router.push(path)
    expect(router.currentRoute.value.path).toBe(path)
  })

  it.each(['coach', 'receptionist', 'admin'] as const)('%s不能进入会员本人资料和订单入口', async role => {
    const { auth, router } = setup(role)
    await auth.login({ username: 'staff_user', password: 'Pass_123' })
    for (const path of ['/profile', '/orders', '/orders/17']) {
      await router.push(path)
      expect(router.currentRoute.value.name).toBe('forbidden')
    }
  })

  it('每个功能声明都有可解析路由和相同的角色合同', () => {
    const { router } = setup()
    expect(new Set(featureRoutes.map(route => route.path)).size).toBe(featureRoutes.length)
    for (const route of featureRoutes) {
      const path = route.path.replace(/:[A-Za-z]+/g, '1')
      expect(router.resolve(path).meta.roles).toEqual(route.roles)
    }
  })

  it('未知路径返回可公开访问的404页', async () => {
    const { router } = setup()
    await router.push('/missing-page')
    expect(router.currentRoute.value.name).toBe('not-found')
  })
})
