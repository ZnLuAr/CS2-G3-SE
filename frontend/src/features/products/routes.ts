import type { FeatureRoute } from '../../shared/navigation'

export const productRoutes: FeatureRoute[] = [
  { path: '/entitlements/cards', title: '我的健身卡', description: '查询本人健身卡权益与余额。', roles: ['member'] },
  { path: '/entitlements/packages', title: '我的课包', description: '查询本人私教课包与剩余课节。', roles: ['member'] },
  { path: '/admin/products', title: '产品管理', description: '维护健身卡与私教课包产品。', roles: ['admin'] },
  { path: '/admin/gift-rules', title: '赠卡规则', description: '查询与管理赠卡规则版本。', roles: ['admin'] },
]
