"""Application-wide bundle of use-case entry points."""

from __future__ import annotations

from dataclasses import dataclass

from .auth_logic import AuthLogic
from .member_logic import MemberLogic
from .product_logic import ProductLogic
from .entitlement_logic import EntitlementLogic
from .sales_logic import SalesLogic
from .course_logic import CourseLogic
from .reservation_logic import ReservationLogic
from .attendance_logic import AttendanceLogic
from .access_logic import AccessLogic
from .measurement_logic import MeasurementLogic
from .review_logic import ReviewLogic
from .report_logic import ReportLogic
from .equipment_logic import EquipmentLogic
from .notification_logic import NotificationLogic
from .recommendation_logic import RecommendationLogic


@dataclass(frozen=True, kw_only=True)
class LogicBundle:
    auth: AuthLogic
    members: MemberLogic
    products: ProductLogic
    sales: SalesLogic
    entitlements: EntitlementLogic
    access: AccessLogic
    courses: CourseLogic
    reservations: ReservationLogic
    attendance: AttendanceLogic
    reviews: ReviewLogic
    equipment: EquipmentLogic
    measurements: MeasurementLogic
    reports: ReportLogic
    notifications: NotificationLogic
    recommendations: RecommendationLogic
