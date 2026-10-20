import { frontRoles, type FeatureRoute } from '../../shared/navigation'

export const memberRoutes: FeatureRoute[] = [
  { path: '/profile', title: '我的资料', description: '查询本人会员资料及关联权益、预约和订单。', roles: ['member'] },
  { path: '/front/members', title: '会员资料', description: '建立会员档案、查询与维护资料。', roles: frontRoles },
  { path: '/admin/members', title: '会员管理', description: '管理会员档案与归档状态。', roles: ['admin'] },
]
