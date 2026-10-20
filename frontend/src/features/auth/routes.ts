import type { FeatureRoute } from '../../shared/navigation'

export const authRoutes: FeatureRoute[] = [
  { path: '/admin/accounts', title: '账号管理', description: '管理账号和会员、教练档案关联。', roles: ['admin'] },
]
