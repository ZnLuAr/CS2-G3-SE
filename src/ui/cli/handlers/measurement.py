"""体测输入、确认与结果展示；授权和事务由 Logic 与服务处理。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal

from src.logic.measurement_logic import MeasurementLogic
from src.models.contracts import Actor, DateWindow, MeasurementInput, MeasurementQuery, Role
from src.ui.cli import formatters, prompts


class MeasurementHandler:
    """采集体测表单并调用用例；取消或拒绝确认时结束交互。"""

    def __init__(
        self,
        logic: MeasurementLogic,
        get_actor: Callable[[], Actor],
        *,
        timezone_name: str,
    ) -> None:
        """接收用例入口、当前身份回调及门店时区。"""
        self._logic = logic
        self._get_actor = get_actor
        self._timezone_name = timezone_name

    @property
    def current_role(self) -> Role:
        """取得菜单展示使用的当前角色，实际权限由服务复核。"""
        return self._get_actor().role

    def record(self) -> None:
        """确认完整表单后录入；输入 q 或拒绝确认不调用写用例。"""
        actor = self._get_actor()
        member_id = prompts.prompt_member_id()
        measured_at = prompts.prompt_datetime(
            "测量时刻（YYYY-MM-DD HH:MM，q 取消）：",
            timezone_name=self._timezone_name,
        )
        height = prompts.prompt_decimal("身高（厘米）：", minimum=Decimal("0"))
        weight = prompts.prompt_decimal("体重（千克）：", minimum=Decimal("0"))
        body_fat = None
        if prompts.prompt_confirm("填写体脂率？"):
            body_fat = prompts.prompt_decimal("体脂率（%）：", minimum=Decimal("0"))
        data = MeasurementInput(
            member_id=member_id,
            measured_at=measured_at,
            height_cm=height,
            weight_kg=weight,
            body_fat_pct=body_fat,
        )
        if not prompts.prompt_confirm("确认保存这次体测？"):
            return
        view = self._logic.record(actor, data)
        print(formatters.format_measurement(view, timezone_name=self._timezone_name))

    def get_measurement(self) -> None:
        """按体测编号查看详情；越权和不存在由服务统一处理。"""
        actor = self._get_actor()
        measurement_id = prompts.prompt_int("体测编号（q 取消）：", minimum=1)
        view = self._logic.get_measurement(actor, measurement_id)
        print(formatters.format_measurement(view, timezone_name=self._timezone_name))

    def list_measurements(self) -> None:
        """按会员和可选时间范围分页浏览；会员默认使用本人编号。"""
        from src.ui.cli.menus import browse_pages

        actor = self._get_actor()
        member_id = (
            actor.member_id
            if actor.role == "member" and actor.member_id is not None
            else prompts.prompt_member_id()
        )
        window = None
        if prompts.prompt_confirm("限定测量时间范围？"):
            window = DateWindow(
                start=prompts.prompt_datetime(
                    "开始时刻（含，YYYY-MM-DD HH:MM）：",
                    timezone_name=self._timezone_name,
                ),
                end=prompts.prompt_datetime(
                    "结束时刻（不含，YYYY-MM-DD HH:MM）：",
                    timezone_name=self._timezone_name,
                ),
            )
        query = MeasurementQuery(member_id=member_id, window=window)
        browse_pages(
            lambda paging: self._logic.list_measurements(actor, replace(query, paging=paging)),
            lambda page: formatters.format_measurements(page, timezone_name=self._timezone_name),
        )

    def compare(self) -> None:
        """按先后两个编号展示变化；可见性和先后顺序由服务校验。"""
        actor = self._get_actor()
        before_id = prompts.prompt_int("对比前体测编号（q 取消）：", minimum=1)
        after_id = prompts.prompt_int("对比后体测编号（q 取消）：", minimum=1)
        view = self._logic.compare(actor, before_id, after_id)
        print(formatters.format_measurement_comparison(view, timezone_name=self._timezone_name))
