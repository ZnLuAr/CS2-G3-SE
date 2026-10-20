import { allRoles, type FeatureRoute } from '../../shared/navigation'

export const equipmentRoutes: FeatureRoute[] = [
  { path: '/equipment', title: '器械与报修', description: '查询器械资料并提交故障报修。', roles: allRoles },
  { path: '/equipment/:equipmentId/fault-report', title: '器械报修', description: '提交选定器械的故障情况。', roles: allRoles, navigation: false },
  { path: '/admin/equipment', title: '器械管理', description: '维护器械资料、维修明细与处理状态。', roles: ['admin'] },
]
