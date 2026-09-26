from __future__ import annotations

from .models import Action


TEMPLATES = {
    Action.SAFE_HANDOFF: "이 역할극은 여기서 멈추고 진행자 또는 사전 안내된 지원 경로로 연결하겠습니다.",
    Action.BOUNDARY_NOTICE: "이 역할극의 범위와 개인정보·관계 경계를 지키기 위해 여기서 멈추고 진행자에게 인계하겠습니다.",
    Action.CLARIFY: "확실히 진행하려면 필요한 정보를 한두 가지 확인해도 될까요?",
    Action.DECOMPOSE: "과제를 더 작은 단계로 나누고, 다음에 할 한 가지를 함께 고르겠습니다.",
    Action.REPLAN_OR_HANDOFF: "현재 범위에서 해결할 수 없는 제약이 있습니다. 필요한 도움이나 목표 조정을 확인하겠습니다.",
    Action.SUPPORT_OPTIONS: "이 역할극에서 지원이 필요하다고 명시됐습니다. 정리, 다음 단계 선택, 진행자 도움 중 무엇이 좋을까요?",
    Action.CONTINUE: "현재 목표에 맞춰 다음 역할극 단계를 진행하겠습니다.",
}


def render(action_plan: dict[str, object]) -> str:
    """Render only the engine-selected action; never infer a user's emotion."""
    return TEMPLATES[Action(action_plan["selected_action"])]
