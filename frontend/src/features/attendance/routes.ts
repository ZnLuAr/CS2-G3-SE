import type { FeatureRoute } from '../../shared/navigation'

export const attendanceRoutes: FeatureRoute[] = [
  { path: '/coach/attendance', title: '到课记录', description: '办理签到、补签、消课与缺席登记。', roles: ['coach'] },
  { path: '/admin/attendance', title: '到课管理', description: '查询到课结算并办理更正。', roles: ['admin'] },
]
