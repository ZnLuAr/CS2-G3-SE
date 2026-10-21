import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'
import { ApiError } from '../../src/shared/api/errors'
import { createAuthStore, SESSION_KEY } from '../../src/features/auth/store'
import { validateLogin } from '../../src/features/auth/validation'
import type { AuthApi, LoginResponse } from '../../src/features/auth/api'
import type { Actor } from '../../src/shared/api/types'

const member: Actor = { accountId: '7', role: 'member', memberId: '12', coachId: null }
const session: LoginResponse = {
  accessToken: 'test-token', tokenType: 'bearer', expiresAt: '2099-01-01T00:00:00Z', actor: member,
}
function setup() {
  const api: AuthApi = {
    login: vi.fn().mockResolvedValue(session),
    me: vi.fn().mockResolvedValue(member),
    logout: vi.fn().mockResolvedValue({ loggedOut: true }),
  }
  const clearPrivateState = vi.fn()
  const auth = createAuthStore({ api, storage: sessionStorage, clearPrivateState })(createPinia())
  return { auth, api, clearPrivateState }
}

beforeEach(() => sessionStorage.clear())
describe('认证会话（模拟 API）', () => {
  it('登录规范化账号，持久化凭据，保留密码原文且不保存密码和身份档案', async () => {
    const { auth, api, clearPrivateState } = setup()
    await auth.login({ username: ' Member_7 ', password: 'Pass_123' })
    expect(api.login).toHaveBeenCalledWith({ username: 'member_7', password: 'Pass_123' })
    expect(auth.actor).toEqual(member)
    expect(JSON.parse(sessionStorage.getItem(SESSION_KEY)!)).toEqual({ accessToken: session.accessToken, expiresAt: session.expiresAt })
    expect(clearPrivateState).toHaveBeenCalledOnce()
  })

  it('刷新恢复时只采纳 /me 的最新角色和关联', async () => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    const { auth, api } = setup()
    const verified: Actor = { accountId: '7', role: 'coach', memberId: null, coachId: '18' }
    vi.mocked(api.me).mockResolvedValue(verified)
    await auth.restoreSession()
    expect(auth.actor).toEqual(verified)
    expect(api.me).toHaveBeenCalledOnce()
  })

  it('并发恢复等待同一次 /me 完成', async () => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    const { auth, api } = setup()
    let resolve!: (actor: Actor) => void
    vi.mocked(api.me).mockReturnValue(new Promise(done => { resolve = done }))
    const first = auth.restoreSession()
    const second = auth.restoreSession()
    resolve(member)
    await Promise.all([first, second])
    expect(api.me).toHaveBeenCalledOnce()
    expect(auth.isAuthenticated).toBe(true)
  })

  it.each(['{broken', JSON.stringify({ accessToken: 'old', expiresAt: '2020-01-01T00:00:00Z' })])('损坏或过期的存储值触发清理', async raw => {
    sessionStorage.setItem(SESSION_KEY, raw)
    const { auth, api, clearPrivateState } = setup()
    await auth.restoreSession()
    expect(auth.isAuthenticated).toBe(false)
    expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
    expect(api.me).not.toHaveBeenCalled()
    expect(clearPrivateState).toHaveBeenCalledOnce()
  })

  it('身份失效时清除凭据和私有缓存', async () => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    const { auth, api, clearPrivateState } = setup()
    vi.mocked(api.me).mockRejectedValue(new ApiError({
      message: '登录已失效', action: 'login', errorType: 'AuthenticationError',
      requestId: null, recordId: null,
    }, 401))
    await auth.restoreSession()
    expect(auth.actor).toBeNull()
    expect(auth.accessToken).toBeNull()
    expect(auth.restoreError).toBeNull()
    expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
    expect(clearPrivateState).toHaveBeenCalledOnce()
  })

  it('身份复核暂时失败时保留凭据并允许重试', async () => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    const { auth, api, clearPrivateState } = setup()
    vi.mocked(api.me).mockRejectedValueOnce(new Error('离线'))
    await auth.restoreSession()
    expect(auth.actor).toBeNull()
    expect(auth.accessToken).toBe(session.accessToken)
    expect(sessionStorage.getItem(SESSION_KEY)).not.toBeNull()
    expect(auth.restoreError).toContain('无法验证')
    expect(clearPrivateState).not.toHaveBeenCalled()

    vi.mocked(api.me).mockResolvedValue(member)
    await auth.retryRestoreSession()
    expect(auth.actor).toEqual(member)
    expect(auth.restoreError).toBeNull()
  })

  it('退出即使网络失败仍清除身份', async () => {
    const { auth, api, clearPrivateState } = setup()
    await auth.login({ username: 'member_7', password: 'Pass_123' })
    vi.mocked(api.logout).mockRejectedValue(new Error('离线'))
    await expect(auth.logout()).rejects.toThrow('离线')
    expect(auth.isAuthenticated).toBe(false)
    expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
    expect(clearPrivateState).toHaveBeenCalledTimes(2)
  })

  it('旧身份复核的迟到结果不会覆盖新登录身份', async () => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    const { auth, api } = setup()
    let resolve!: (actor: Actor) => void
    vi.mocked(api.me).mockReturnValue(new Promise(done => { resolve = done }))
    const restoring = auth.restoreSession()
    const admin: Actor = { accountId: '1', role: 'admin', memberId: null, coachId: null }
    vi.mocked(api.login).mockResolvedValue({ ...session, actor: admin })
    await auth.login({ username: 'admin', password: 'Pass_123' })
    resolve(member)
    await restoring
    expect(auth.actor).toEqual(admin)
  })

  it.each(['success', 'failure'] as const)('旧退出请求迟到%s时不会清除新登录身份', async outcome => {
    const { auth, api } = setup()
    await auth.login({ username: 'member_7', password: 'Pass_123' })
    let resolve!: (result: { loggedOut: true }) => void
    let reject!: (error: Error) => void
    vi.mocked(api.logout).mockReturnValue(new Promise((done, fail) => { resolve = done; reject = fail }))
    const loggingOut = auth.logout()
    const loggedOut = loggingOut.catch(() => undefined)
    const admin: Actor = { accountId: '1', role: 'admin', memberId: null, coachId: null }
    vi.mocked(api.login).mockResolvedValue({ ...session, accessToken: 'new-token', actor: admin })
    await auth.login({ username: 'admin', password: 'Pass_123' })
    if (outcome === 'success') resolve({ loggedOut: true })
    else reject(new Error('旧连接中断'))
    await loggedOut
    expect(auth.actor).toEqual(admin)
    expect(auth.accessToken).toBe('new-token')
    expect(JSON.parse(sessionStorage.getItem(SESSION_KEY)!).accessToken).toBe('new-token')
  })
})

describe('登录字段合同', () => {
  it('接受规范化账号及合法密码', () => {
    expect(validateLogin({ username: ' Member_7 ', password: 'Pass_123-' })).toBeNull()
  })
  it.each([
    { username: 'a', password: 'Pass_123' },
    { username: 'member@example.com', password: 'Pass_123' },
    { username: 'member', password: 'bad x!' },
    { username: 'member', password: 'x'.repeat(33) },
  ])('拒绝不符合后端格式的输入', input => {
    expect(validateLogin(input)).toBeTypeOf('string')
  })
})
