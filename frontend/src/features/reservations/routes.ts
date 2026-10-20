import { frontRoles, type FeatureRoute } from '../../shared/navigation'

export const reservationRoutes: FeatureRoute[] = [
  { path: '/bookings', title: '我的预约', description: '查看本人预约与取消结果。', roles: ['member'] },
  { path: '/waitlist', title: '我的候补', description: '查看本人候补位置与处理结果。', roles: ['member'] },
  { path: '/coach/waitlist', title: '课次候补人数', description: '查看本人课次的候补人数。', roles: ['coach'] },
  { path: '/front/bookings', title: '预约办理', description: '为会员查询并办理课次预约。', roles: frontRoles },
  { path: '/front/waitlist', title: '候补办理', description: '为会员查询并办理候补。', roles: frontRoles },
]
