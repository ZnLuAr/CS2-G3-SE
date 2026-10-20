import { inject, type InjectionKey, type Ref } from 'vue'
import type { AuthStore } from '../features/auth/store'

export interface AppContext {
  auth: AuthStore
  fatalMessage: Ref<string | null>
}
export const appContextKey: InjectionKey<AppContext> = Symbol('appContext')
export function useAppContext(): AppContext {
  const context = inject(appContextKey)
  if (!context) throw new Error('应用上下文尚未装配')
  return context
}
