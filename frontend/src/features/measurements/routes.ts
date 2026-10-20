import type { FeatureRoute } from '../../shared/navigation'

export const measurementRoutes: FeatureRoute[] = [
  { path: '/measurements', title: '我的体测', description: '查询本人体测历史与对比结果。', roles: ['member'] },
  { path: '/coach/members/:memberId/measurements', title: '会员体测', description: '按授权录入体测并查询可见历史。', roles: ['coach'], navigation: false },
]
