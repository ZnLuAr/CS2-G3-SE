import type { Role } from './api/types'

export interface FeatureRoute {
  path: string
  title: string
  description: string
  roles: Role[]
  navigation?: boolean
}

export const allRoles: Role[] = ['member', 'coach', 'receptionist', 'admin']
export const frontRoles: Role[] = ['receptionist', 'admin']
export const roleLabels: Record<Role, string> = {
  member: '会员', coach: '教练', receptionist: '前台', admin: '管理员',
}
export const roleHome: Record<Role, string> = {
  member: '/sessions', coach: '/coach/sessions', receptionist: '/front/members', admin: '/admin/accounts',
}
