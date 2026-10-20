import axios, { type AxiosRequestConfig } from 'axios'
import { toApiError, type ApiError } from './errors'

interface ClientOptions {
  baseURL: string
  getAccessToken: () => string | null
  onError: (error: ApiError) => void
}

export function createApiClient(options: ClientOptions) {
  const http = axios.create({ baseURL: options.baseURL, timeout: 15_000 })
  let sessionController = new AbortController()

  /** 身份切换时终止旧请求，防止旧账号数据进入新会话。 */
  function cancelRequests(): void {
    sessionController.abort()
    sessionController = new AbortController()
  }

  async function request<T>(config: AxiosRequestConfig): Promise<T> {
    const token = options.getAccessToken()
    const activeSession = sessionController.signal
    const signal = config.signal
      ? AbortSignal.any([activeSession, config.signal as AbortSignal])
      : activeSession
    try {
      const response = await http.request<T>({
        ...config,
        signal,
        headers: { ...config.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      })
      // 测试适配器或服务工作线程可能在中止后仍返回响应。
      if (signal.aborted) throw new axios.CanceledError()
      return response.data
    } catch (error) {
      if (axios.isCancel(error) || signal.aborted) throw new axios.CanceledError()
      const mapped = toApiError(error)
      options.onError(mapped)
      throw mapped
    }
  }

  return { request, cancelRequests }
}

export type ApiClient = ReturnType<typeof createApiClient>
