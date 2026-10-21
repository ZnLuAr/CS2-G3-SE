import type { FeatureRoute } from '../../shared/navigation'

export const notificationRoutes: FeatureRoute[] = [
  { path: '/notifications', title: '我的通知', description: '查看本人的预约、候补通知与已读状态。', roles: ['member'] },
]
