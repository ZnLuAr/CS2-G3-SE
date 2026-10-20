import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import StatusPage from '../../src/app/StatusPage.vue'
import { appContextKey } from '../../src/app/context'
import type { AuthStore } from '../../src/features/auth/store'

function mountStatusPage(restoreError: string | null, fatal: string | null) {
  const auth = {
    actor: null,
    restoreError,
    retryRestoreSession: vi.fn(),
  } as unknown as AuthStore
  const fatalMessage = ref(fatal)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div>首页</div>' } }],
  })
  const wrapper = mount(StatusPage, {
    props: { kind: 'unavailable' },
    global: {
      plugins: [router],
      provide: { [appContextKey as symbol]: { auth, fatalMessage } },
    },
  })
  return { wrapper, auth, fatalMessage, router }
}

describe('服务状态页恢复入口', () => {
  it('身份恢复故障时提供重新验证并隐藏无效的首页链接', async () => {
    const { wrapper, auth } = mountStatusPage('身份服务暂不可用', null)

    expect(wrapper.get('[role="alert"]').text()).toContain('身份服务暂不可用')
    await wrapper.get('button').trigger('click')
    expect(auth.retryRestoreSession).toHaveBeenCalledOnce()
    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('普通服务故障显示返回首页并清除故障路由状态', async () => {
    const { wrapper, fatalMessage, router } = mountStatusPage(null, '数据库暂不可用')

    expect(wrapper.find('button').exists()).toBe(false)
    await wrapper.get('a').trigger('click')
    expect(fatalMessage.value).toBeNull()
    expect(router.currentRoute.value.path).toBe('/')
  })
})
