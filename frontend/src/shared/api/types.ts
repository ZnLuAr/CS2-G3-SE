/** 与后端 HTTP camelCase 字段一致；日期时间使用带时区 ISO 8601 字符串。 */
export type Role = 'member' | 'coach' | 'receptionist' | 'admin'

/** 业务编号保留十进制字符串，完整表达后端 BIGINT 的正数范围。 */
export type EntityId = string

export function isEntityId(value: unknown): value is EntityId {
  return typeof value === 'string'
    && /^[1-9][0-9]{0,18}$/.test(value)
    && (value.length < 19 || value <= '9223372036854775807')
}

export interface Actor {
  accountId: EntityId
  role: Role
  memberId: EntityId | null
  coachId: EntityId | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface PageRequest {
  page: number
  pageSize: number
}

export type ErrorAction = 'continue' | 'login' | 'exit' | 'verify'

export interface ApiErrorPayload {
  message: string
  action: ErrorAction
  errorType: string
  requestId: string | null
  recordId: EntityId | null
  fields?: string[]
}
