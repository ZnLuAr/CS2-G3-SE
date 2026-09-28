"""v3 迁移辅助存储模型。当前仅声明字段，尚未配置 ORM 映射。

这些表用于停机迁移期间记录进度与新旧编号映射，供中断后恢复和核对。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class SchemaMigrationRun:
    """对应 schema_migration_runs 表的存储字段；尚未配置 ORM 映射。"""

    target_version: int
    phase: str
    structure_fingerprint: str
    started_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class V3MemberMap:
    """对应 v3_member_map 表的存储字段；尚未配置 ORM 映射。"""

    old_member_id: int
    member_id: int


@dataclass(frozen=True, kw_only=True)
class V3ProductMap:
    """对应 v3_product_map 表的存储字段；尚未配置 ORM 映射。"""

    old_product_id: int
    gym_card_product_id: int | None
    lesson_package_product_id: int | None
    historical_gift_rule_id: int | None


@dataclass(frozen=True, kw_only=True)
class V3SaleMap:
    """对应 v3_sale_map 表的存储字段；尚未配置 ORM 映射。"""

    old_membership_id: int
    sale_order_id: int
    sale_item_id: int
    payment_id: int


@dataclass(frozen=True, kw_only=True)
class V3EntitlementMap:
    """对应 v3_entitlement_map 表的存储字段；尚未配置 ORM 映射。"""

    old_membership_id: int
    lesson_package_id: int | None
    gift_grant_id: int | None
    gym_card_id: int


@dataclass(frozen=True, kw_only=True)
class V3OperationMap:
    """对应 v3_operation_map 表的存储字段；尚未配置 ORM 映射。"""

    old_operation_record_id: int
    operation_record_id: int
    legacy_operation: str
    target_operation: str
    target_result_type: str
    target_result_id: int
    legacy_payload_hash: str
    payload_version: str
    migrated_at: datetime


@dataclass(frozen=True, kw_only=True)
class V3EntryMap:
    """对应 v3_entry_map 表的存储字段；尚未配置 ORM 映射。"""

    old_gym_entry_id: int
    gym_entry_id: int
