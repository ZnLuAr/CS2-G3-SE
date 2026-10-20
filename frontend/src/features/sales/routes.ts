import { frontRoles, type FeatureRoute } from '../../shared/navigation'

export const salesRoutes: FeatureRoute[] = [
  { path: '/orders', title: '我的订单', description: '查询本人销售订单、付款和产生的权益。', roles: ['member'] },
  { path: '/orders/:orderId', title: '订单详情', description: '查看本人订单的付款、权益及赠送记录。', roles: ['member'], navigation: false },
  { path: '/front/sales', title: '销售办理', description: '办理健身卡与私教课包销售。', roles: frontRoles },
  { path: '/front/orders', title: '订单查询', description: '查询会员订单与销售结果。', roles: frontRoles },
  { path: '/front/payments', title: '收款记录', description: '查询收款流水与明细。', roles: frontRoles },
  { path: '/front/entries', title: '入场登记', description: '核实会员权益并办理入场。', roles: frontRoles },
]
