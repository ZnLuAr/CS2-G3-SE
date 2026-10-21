import type { FeatureRoute } from '../../shared/navigation'

export const courseRoutes: FeatureRoute[] = [
  { path: '/sessions', title: '课程安排', description: '浏览即将开课的课次与预约入口。', roles: ['member'] },
  { path: '/sessions/:sessionId', title: '课次详情', description: '查看课次时间、教练与可用余位。', roles: ['member'], navigation: false },
  { path: '/coach/sessions', title: '我的课表', description: '查看本人授课安排与学员名单。', roles: ['coach'] },
  { path: '/coach/sessions/:sessionId/attendees', title: '学员名单', description: '查看本课学员及到课情况。', roles: ['coach'], navigation: false },
  { path: '/admin/coaches', title: '教练管理', description: '维护教练资料与状态。', roles: ['admin'] },
  { path: '/admin/courses', title: '课程管理', description: '维护课程模板与课程标签。', roles: ['admin'] },
  { path: '/admin/venues', title: '场地管理', description: '维护上课场地与可用状态。', roles: ['admin'] },
  { path: '/admin/sessions', title: '排课管理', description: '创建与管理课次安排。', roles: ['admin'] },
]
