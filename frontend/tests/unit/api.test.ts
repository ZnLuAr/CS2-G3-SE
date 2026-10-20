import { describe, expect, it, vi } from 'vitest'
import axios, { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { createApiClient } from '../../src/shared/api/client'
import { toApiError } from '../../src/shared/api/errors'
import { isEntityId } from '../../src/shared/api/types'

describe('共享 HTTP 客户端（模拟传输）', () => {
  it('使用当前凭据并直接返回后端分页结构', async () => {
    let request: InternalAxiosRequestConfig | undefined
    const page = { items: [{ id: '9007199254740993' }], total: 1, page: 1, pageSize: 20 }
    const http = axios.create({ adapter: async config => {
      request = config
      return { data: JSON.stringify(page), status: 200, statusText: 'OK', headers: { 'content-type': 'application/json' }, config }
    } })
    vi.spyOn(axios, 'create').mockReturnValue(http)
    const client = createApiClient({ baseURL: '/api', getAccessToken: () => 'token', onError: vi.fn() })
    expect(await client.request({ url: '/test' })).toEqual(page)
    expect(request?.headers.Authorization).toBe('Bearer token')
  })

  it('旧会话请求中止后不能把响应交给调用方', async () => {
    let resolve!: (response: AxiosResponse) => void
    let config!: InternalAxiosRequestConfig
    const http = axios.create({ adapter: value => {
      config = value
      return new Promise(done => { resolve = done })
    } })
    vi.spyOn(axios, 'create').mockReturnValue(http)
    const onError = vi.fn()
    const client = createApiClient({ baseURL: '/api', getAccessToken: () => 'old', onError })
    const pending = client.request({ url: '/private' })
    client.cancelRequests()
    resolve({ data: { private: true }, status: 200, statusText: 'OK', headers: {}, config })
    await expect(pending).rejects.toSatisfy(axios.isCancel)
    expect(onError).not.toHaveBeenCalled()
  })

  it('旧会话迟到的401不会触发新会话的身份清理', async () => {
    let reject!: (error: AxiosError) => void
    let config!: InternalAxiosRequestConfig
    const http = axios.create({ adapter: value => {
      config = value
      return new Promise((_, fail) => { reject = fail })
    } })
    vi.spyOn(axios, 'create').mockReturnValue(http)
    const onError = vi.fn()
    const client = createApiClient({ baseURL: '/api', getAccessToken: () => 'old-token', onError })
    const pending = client.request({ url: '/private' })
    client.cancelRequests()
    reject(new AxiosError('invalid', 'ERR_BAD_REQUEST', config, undefined, {
      status: 401,
      data: { message: '旧身份已失效', action: 'login', errorType: 'AuthenticationError', requestId: null, recordId: null },
      statusText: 'Unauthorized', headers: {}, config,
    }))
    await expect(pending).rejects.toSatisfy(axios.isCancel)
    expect(onError).not.toHaveBeenCalled()
  })

  it('保留结果未知的 action 和核实编号', () => {
    const payload = { message: '结果待核实', action: 'verify', errorType: 'OutcomeUnknownError', requestId: '550e8400-e29b-41d4-a716-446655440000', recordId: '9223372036854775807' }
    const error = new AxiosError('failure', 'ERR_BAD_RESPONSE', undefined, undefined,
      { status: 503, data: payload } as AxiosResponse)
    expect(toApiError(error).payload).toEqual(payload)
  })

  it('非标准 401 同样引导重新登录，不展示原始响应', () => {
    const error = new AxiosError('secret password!', 'ERR_BAD_REQUEST', undefined, undefined,
      { status: 401, data: '<html>secret password!</html>' } as AxiosResponse)
    expect(toApiError(error).payload.action).toBe('login')
    expect(toApiError(error).message).not.toContain('secret')
  })

  it.each(['1', '9007199254740993', '9223372036854775807'])('保留完整业务编号%s', id => {
    expect(isEntityId(id)).toBe(true)
  })

  it.each(['0', '01', '-1', '1.0', '1e3', ' 1', '9223372036854775808', 1])('拒绝非规范或越界业务编号%s', id => {
    expect(isEntityId(id)).toBe(false)
    const error = new AxiosError('unsafe', 'ERR_BAD_RESPONSE', undefined, undefined, {
      status: 503,
      data: { message: '不可信原文', action: 'verify', errorType: 'OutcomeUnknownError', requestId: null, recordId: id },
    } as AxiosResponse)
    expect(toApiError(error).payload.recordId).toBeNull()
    expect(toApiError(error).message).not.toContain('不可信原文')
  })
})
