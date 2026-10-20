import { frontRoles, type FeatureRoute } from '../../shared/navigation'

export const recommendationRoutes: FeatureRoute[] = [
  { path: '/recommendations', title: '课程推荐', description: '查看适合本人的课程与推荐理由。', roles: ['member'] },
  { path: '/front/recommendations', title: '会员课程推荐', description: '选择会员并查询课程推荐。', roles: frontRoles },
]
