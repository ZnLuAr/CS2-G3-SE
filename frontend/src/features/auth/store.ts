import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError } from '../../shared/api/errors'
import type { Actor } from '../../shared/api/types'
import type { AuthApi, LoginInput } from './api'

export const SESSION_KEY = 'gym.session'

interface StoredSession { accessToken: string; expiresAt: string }
interface AuthDependencies {
  api: AuthApi
  storage: Storage
  clearPrivateState: () => void
}

/** 凭据按浏览器标签页保存；恢复后通过 /me 复核角色及档案关联。 */
export function createAuthStore(deps: AuthDependencies) {
  return defineStore('auth', () => {
    const actor = ref<Actor | null>(null)
    const accessToken = ref<string | null>(null)
    const expiresAt = ref<string | null>(null)
    const restoreError = ref<string | null>(null)
    const isAuthenticated = computed(() => actor.value !== null && accessToken.value !== null)
    let restored = false
    let generation = 0
    let restoration: Promise<void> | null = null

    function removeStoredSession(): void {
      try { deps.storage.removeItem(SESSION_KEY) } catch { /* 浏览器禁用存储时仍可结束内存会话。 */ }
    }

    function clearSession(): void {
      generation += 1
      actor.value = null
      accessToken.value = null
      expiresAt.value = null
      restoreError.value = null
      restored = true
      removeStoredSession()
      deps.clearPrivateState()
    }

    function hasExpired(): boolean {
      return expiresAt.value !== null && Date.parse(expiresAt.value) <= Date.now()
    }

    function persist(session: StoredSession): void {
      try { deps.storage.setItem(SESSION_KEY, JSON.stringify(session)) } catch { /* 内存会话可继续使用。 */ }
    }

    async function login(input: LoginInput): Promise<void> {
      clearSession()
      const currentGeneration = generation
      const session = await deps.api.login({ username: input.username.trim().toLowerCase(), password: input.password })
      if (generation !== currentGeneration) return
      accessToken.value = session.accessToken
      expiresAt.value = session.expiresAt
      actor.value = session.actor
      persist({ accessToken: session.accessToken, expiresAt: session.expiresAt })
    }

    async function restoreSession(): Promise<void> {
      if (hasExpired()) clearSession()
      if (restoration) return restoration
      if (restored) return
      restored = true
      const currentGeneration = generation
      restoration = (async () => {
        restoreError.value = null
        let session: StoredSession
        try {
          const raw = deps.storage.getItem(SESSION_KEY)
          if (!raw) return
          session = JSON.parse(raw) as StoredSession
          if (typeof session.accessToken !== 'string' || !session.accessToken
            || typeof session.expiresAt !== 'string'
            || !Number.isFinite(Date.parse(session.expiresAt))
            || Date.parse(session.expiresAt) <= Date.now()) {
            clearSession()
            return
          }
        } catch {
          clearSession()
          return
        }
        accessToken.value = session.accessToken
        expiresAt.value = session.expiresAt
        try {
          const verified = await deps.api.me()
          if (generation === currentGeneration) actor.value = verified
        } catch (error) {
          if (generation !== currentGeneration) return
          if (error instanceof ApiError && error.payload.action === 'login') {
            clearSession()
            return
          }
          restoreError.value = error instanceof ApiError
            ? error.message
            : '暂时无法验证当前身份，请稍后重试。'
        }
      })()
      try { await restoration } finally { restoration = null }
    }

    async function retryRestoreSession(): Promise<void> {
      if (!restoreError.value) return
      restored = false
      await restoreSession()
    }

    async function logout(): Promise<void> {
      const currentGeneration = generation
      try { if (accessToken.value) await deps.api.logout() } finally {
        if (generation === currentGeneration) clearSession()
      }
    }

    return {
      actor, accessToken, expiresAt, restoreError, isAuthenticated,
      login, logout, restoreSession, retryRestoreSession, clearSession,
    }
  })
}

export type AuthStore = ReturnType<ReturnType<typeof createAuthStore>>
