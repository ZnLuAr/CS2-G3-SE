import axios from 'axios'
import { isEntityId, type ApiErrorPayload } from './types'

export class ApiError extends Error {
  constructor(readonly payload: ApiErrorPayload, readonly status: number | null) {
    super(payload.message)
    this.name = 'ApiError'
  }
}

function isErrorPayload(value: unknown): value is ApiErrorPayload {
  if (!value || typeof value !== 'object') return false
  const data = value as Record<string, unknown>
  return typeof data.message === 'string'
    && typeof data.action === 'string'
    && ['continue', 'login', 'exit', 'verify'].includes(String(data.action))
    && typeof data.errorType === 'string'
    && (data.requestId === null || typeof data.requestId === 'string')
    && (data.recordId === null || isEntityId(data.recordId))
}

/** 安全地映射 HTTP/网络失败；保留结果核实编号，不拼接原始请求或响应。 */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  const status = axios.isAxiosError(error) ? error.response?.status ?? null : null
  if (axios.isAxiosError(error) && isErrorPayload(error.response?.data)) {
    return new ApiError(error.response.data, status)
  }
  return new ApiError({
    message: status === 401 ? '登录已失效，请重新登录。' : '暂时无法连接服务，请稍后重试。',
    action: status === 401 ? 'login' : 'continue',
    errorType: status === null ? 'NetworkError' : 'HttpError',
    requestId: null,
    recordId: null,
  }, status)
}
