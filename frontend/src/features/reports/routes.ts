import type { FeatureRoute } from '../../shared/navigation'

export const reportRoutes: FeatureRoute[] = [
  { path: '/admin/reports', title: '经营统计', description: '查询经营、权益、课程及教练统计。', roles: ['admin'] },
  { path: '/admin/logs', title: '运行日志', description: '按固定快照查询脱敏日志。', roles: ['admin'] },
]
