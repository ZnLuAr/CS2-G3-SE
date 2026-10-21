import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import LoadingState from '../../src/shared/components/LoadingState.vue'
import EmptyState from '../../src/shared/components/EmptyState.vue'
import ErrorState from '../../src/shared/components/ErrorState.vue'

describe('共享状态组件', () => {
  it('加载反馈可被辅助技术读取', () => {
    const wrapper = mount(LoadingState)
    expect(wrapper.get('[role="status"]').text()).toContain('正在加载')
  })
  it('空结果可以提供自定义下一步', () => {
    const wrapper = mount(EmptyState, { props: { title: '暂无预约', message: '浏览课次后预约。' }, slots: { default: '<a href="/sessions">浏览课次</a>' } })
    expect(wrapper.text()).toContain('暂无预约')
    expect(wrapper.get('a').attributes('href')).toBe('/sessions')
  })
  it('失败组件显示安全提示并允许重试', async () => {
    const wrapper = mount(ErrorState, { props: { message: '请求失败，请重试。', retryable: true } })
    expect(wrapper.get('[role="alert"]').text()).toContain('请求失败')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
})
