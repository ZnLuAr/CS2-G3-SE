import type { LoginInput } from './api'

/** 与后端 LoginRequest 同步：用户名去空格转小写，密码保留原文。 */
export function validateLogin(input: LoginInput): string | null {
  if (!/^[a-z0-9_]{3,50}$/.test(input.username.trim().toLowerCase())) {
    return '账号需为 3–50 位字母、数字或下划线。'
  }
  if (!/^[A-Za-z0-9_-]{6,32}$/.test(input.password)) {
    return '密码需为 6–32 位字母、数字、下划线或短横线。'
  }
  return null
}
