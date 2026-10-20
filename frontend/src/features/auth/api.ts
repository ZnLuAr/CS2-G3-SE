import type { ApiClient } from '../../shared/api/client'
import type { Actor } from '../../shared/api/types'

export interface LoginInput { username: string; password: string }
export interface LoginResponse {
  accessToken: string
  tokenType: 'bearer'
  expiresAt: string
  actor: Actor
}
export interface LogoutResponse { loggedOut: true }

export function createAuthApi(client: ApiClient) {
  return {
    login: (input: LoginInput) => client.request<LoginResponse>({ method: 'POST', url: '/auth/login', data: input }),
    me: () => client.request<Actor>({ method: 'GET', url: '/auth/me' }),
    logout: () => client.request<LogoutResponse>({ method: 'POST', url: '/auth/logout' }),
  }
}

export type AuthApi = ReturnType<typeof createAuthApi>
