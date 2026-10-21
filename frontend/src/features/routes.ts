import { authRoutes } from './auth/routes'
import { memberRoutes } from './members/routes'
import { productRoutes } from './products/routes'
import { salesRoutes } from './sales/routes'
import { courseRoutes } from './courses/routes'
import { reservationRoutes } from './reservations/routes'
import { attendanceRoutes } from './attendance/routes'
import { reviewRoutes } from './reviews/routes'
import { measurementRoutes } from './measurements/routes'
import { equipmentRoutes } from './equipment/routes'
import { reportRoutes } from './reports/routes'
import { notificationRoutes } from './notifications/routes'
import { recommendationRoutes } from './recommendations/routes'

export const featureRoutes = [
  ...authRoutes, ...memberRoutes, ...productRoutes, ...salesRoutes, ...courseRoutes,
  ...reservationRoutes, ...attendanceRoutes, ...reviewRoutes, ...measurementRoutes,
  ...equipmentRoutes, ...reportRoutes, ...notificationRoutes, ...recommendationRoutes,
]
