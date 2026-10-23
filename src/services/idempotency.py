"""请求编号与输入摘要工具，供排课、取消课次、预约和取消预约共用。

为什么需要：
1. 提交结果未知时，界面让用户按原 `request_id` 查询，不能自动重试；
2. 同一请求编号携带不同输入时，服务必须拒绝，避免一个编号对应两次不同操作；
3. 摘要只包含业务输入，不包含密码等敏感字段。

摘要格式按设计：
- JSON 键排序、紧凑分隔、UTF-8；
- Decimal 保留两位小数；
- date 用 YYYY-MM-DD；
- datetime 转 UTC 后使用带 `+00:00` 的 ISO 字符串；
- 对 UTF-8 字节计算 SHA-256，输出小写十六进制。
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from src.errors.business import ConflictError, InvalidInputError
from src.models.operation import OperationRecord

MAX_REQUEST_ID_LENGTH = 64


def validate_request_id(request_id: str) -> str:
    """检查并返回请求编号。

    界面用 UUID 生成，服务只要求非空且不超过数据库列长度；这样测试和手工
    核实时也能使用可读编号，同时避免超长值写入时被数据库截断。
    """
    if not isinstance(request_id, str):
        raise InvalidInputError("请求编号必须是文字")
    value = request_id.strip()
    if not value:
        raise InvalidInputError("请求编号不能为空")
    if len(value) > MAX_REQUEST_ID_LENGTH:
        raise InvalidInputError(f"请求编号不能超过 {MAX_REQUEST_ID_LENGTH} 个字符")
    return value


def _canonical(value: Any) -> Any:
    """把输入值转换成固定 JSON 表示；不支持的嵌套结构直接拒绝。"""
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise InvalidInputError("时间必须带时区")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    raise InvalidInputError("请求内容包含无法摘要的字段")


def payload_hash(values: dict[str, Any]) -> str:
    """计算业务输入的 SHA-256 摘要。

    例子：排课请求包含课程、教练、场地、起止时间和容量；同一请求编号重试时
    这些值必须完全一致，否则说明用户改过表单，应生成新的请求编号。
    """
    payload = json.dumps(
        _canonical(values),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ensure_replay_matches(
    record: OperationRecord,
    *,
    actor_id: int,
    operation: str,
    payload: str,
) -> None:
    """核对原操作记录是否属于同一操作者、同一操作和同一输入。

    不匹配时抛 ConflictError，提示用户换一个请求编号或先核实原结果；
    匹配时调用方直接返回原结果，不重复写业务数据。
    """
    if (
        record.actor_id != actor_id
        or record.operation != operation
        or record.payload_hash != payload
    ):
        raise ConflictError("请求编号已被其他操作使用，请核实原结果或换一个编号")
