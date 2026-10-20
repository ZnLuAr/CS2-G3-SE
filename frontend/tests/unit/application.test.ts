import { beforeEach, describe, expect, it, vi } from 'vitest'
import axios, { AxiosError, type AxiosResponse } from 'axios'
import { createMemoryHistory } from 'vue-router'
import { createApplication } from '../../src/app/createApplication'
import { SESSION_KEY } from '../../src/features/auth/store'

const actor = { accountId: '7', role: 'member', memberId: '12', coachId: null }
beforeEach(() => sessionStorage.clear())

describe('应用身份与缓存装配（模拟传输）', () => {
  it('空的API地址回退到同源/api前缀', async () => {
    let baseURL: string | undefined
    const http = axios.create({ adapter: async config => {
      baseURL = config.baseURL
      return { data: null, status: 200, statusText: 'OK', headers: {}, config }
    } })
    const createHttp = vi.spyOn(axios, 'create').mockImplementation(config => {
      http.defaults.baseURL = config?.baseURL
      return http
    })
    const runtime = createApplication({ history: createMemoryHistory(), storage: sessionStorage, baseURL: '' })
    await runtime.client.request({ url: '/auth/me' })
    expect(createHttp).toHaveBeenCalledWith({ baseURL: '/api', timeout: 15_000 })
    expect(baseURL).toBe('/api')
  })

  it('登录切换清除已有账号查询缓存，401再次清理并转向登录', async () => {
    const http = axios.create({ adapter: async config => {
      if (config.url === '/auth/login') {
        return { data: { actor, accessToken: 'token', tokenType: 'bearer', expiresAt: '2099-01-01T00:00:00Z' }, status: 200, statusText: 'OK', headers: {}, config }
      }
      throw new AxiosError('invalid', 'ERR_BAD_REQUEST', config, undefined, {
        data: { message: '身份已失效', action: 'login', errorType: 'AuthenticationError', requestId: null, recordId: null },
        status: 401, statusText: 'Unauthorized', headers: {}, config,
      })
    } })
    vi.spyOn(axios, 'create').mockReturnValue(http)
    const runtime = createApplication({ history: createMemoryHistory(), storage: sessionStorage })
    await runtime.router.push('/login')
    runtime.queryClient.setQueryData(['old-account', 'bookings'], { private: true })
    await runtime.auth.login({ username: 'member', password: 'Pass_123' })
    expect(runtime.queryClient.getQueryCache().getAll()).toHaveLength(0)
    runtime.queryClient.setQueryData(['member', 'bookings'], { private: true })
    await runtime.router.push('/sessions')
    await expect(runtime.client.request({ url: '/private' })).rejects.toMatchObject({ status: 401 })
    expect(runtime.auth.actor).toBeNull()
    expect(runtime.queryClient.getQueryCache().getAll()).toHaveLength(0)
    expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
    await vi.waitFor(() => expect(runtime.router.currentRoute.value.name).toBe('login'))
  })

  it('exit错误显示服务不可用页且保留安全反馈', async () => {
    const http = axios.create({ adapter: async config => {
      throw new AxiosError('failure', 'ERR_BAD_RESPONSE', config, undefined, {
        data: { message: '服务暂时不可用', action: 'exit', errorType: 'StorageError', requestId: null, recordId: null },
        status: 503, statusText: 'Unavailable', headers: {}, config,
      } as AxiosResponse)
    } })
    vi.spyOn(axios, 'create').mockReturnValue(http)
    const runtime = createApplication({ history: createMemoryHistory(), storage: sessionStorage })
    await runtime.router.push('/login')
    await expect(runtime.client.request({ url: '/test' })).rejects.toMatchObject({ status: 503 })
    await vi.waitFor(() => expect(runtime.router.currentRoute.value.name).toBe('unavailable'))
    expect(runtime.fatalMessage.value).toBe('服务暂时不可用')
  })

  it('身份恢复时发生exit错误保留凭据并显示重试页面', async () => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({
      accessToken: 'token', expiresAt: '2099-01-01T00:00:00Z',
    }))
    const http = axios.create({ adapter: async config => {
      throw new AxiosError('failure', 'ERR_BAD_RESPONSE', config, undefined, {
        data: { message: '服务暂时不可用', action: 'exit', errorType: 'StorageError', requestId: null, recordId: null },
        status: 503, statusText: 'Unavailable', headers: {}, config,
      } as AxiosResponse)
    } })
    vi.spyOn(axios, 'create').mockReturnValue(http)
    const runtime = createApplication({ history: createMemoryHistory(), storage: sessionStorage })
    await runtime.router.push('/sessions')
    expect(runtime.router.currentRoute.value.name).toBe('unavailable')
    expect(runtime.fatalMessage.value).toBe('服务暂时不可用')
    expect(runtime.auth.actor).toBeNull()
    expect(sessionStorage.getItem(SESSION_KEY)).not.toBeNull()
    expect(runtime.auth.restoreError).toBe('服务暂时不可用')
  })
})
