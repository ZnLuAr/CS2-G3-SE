import type { FeatureRoute } from '../../shared/navigation'

export const reviewRoutes: FeatureRoute[] = [
  { path: '/reviews', title: '我的评价', description: '评价已完成预约并查询本人评价历史。', roles: ['member'] },
  { path: '/coach/reviews', title: '课次评价', description: '查询本人授课课次的评价。', roles: ['coach'] },
  { path: '/admin/reviews', title: '评价查询', description: '查询课程评价。', roles: ['admin'] },
]
