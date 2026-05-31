# core/schemas.py
"""
no-title에서 사용하는 Agent의 도메인 스키마 정의 모듈

Agent의 정체성을 표현하는 pydantic 모델 두 개를 정의한다.
- Trait: Persona를 이루는 특성. "강화"의 단위가 된다.
- Persona: Agent의 정체성. Trait 여러 개를 담는 그릇이 된다.

설계 철학:
    페르소나는 자유 텍스트가 아니라 "조절 가능한 수치들의 집합"으로 표현된다.
    그래야 대화를 통해 성격이 강화되는 루프(SEED → CONVERSE → REFLECT →
    REINFORCE)에서 각 특성의 강도를 정량적으로 갱신할 수 있다.

    하이브리드 강화 정책:
    - core 특성은 시드 시점 강도로 수렴 (일관성 보장)
    - evolved 특성은 대화를 통해 자유롭게 진화 (성장 느낌)
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List


class Trait(BaseModel):
    """
    Persona를 이루는 낱개 특성 하나.

    Persona 안에 여러 개가 담기며, 각 Trait는 독립적으로 강도가 변화한다.
    강화 루프에서 "강화"되는 실제 대상이 바로 이 Trait의 strength 필드다.

    종류 (kind):
        - "core":    사용자가 시드로 직접 부여한 특성. 강화 시 seed_strength로
                     수렴하는 힘이 작용해 일관성이 유지된다.
        - "evolved": 대화 과정에서 형성된 특성. 수렴 제약 없이 자유 진화한다.

    강도(strength)는 0.0~1.0 범위로 제한된다. 대화에서 발현될 때마다 올라가고,
    오래 발현되지 않으면 last_expressed 기반의 감쇠(decay)로 서서히 떨어진다.
    """

    name: str = Field(
        description="특성을 식별하는 키워드. 형용사 또는 명사 (예: '호기심', '냉소적', '따뜻함')."
    )
    strength: float = Field(
        ge=0.0,
        le=1.0,
        description="현재 발현 강도. 0.0(없음)~1.0(매우 강함). 강화 루프가 갱신하는 유일한 동적 값.",
    )
    kind: Literal["core", "evolved"] = Field(
        description="'core'면 시드 부여 특성(seed_strength로 수렴), 'evolved'면 대화로 형성된 특성(자유 진화)."
    )
    seed_strength: float = Field(
        ge=0.0,
        le=1.0,
        description="시드 시점의 강도. core 특성을 수렴시킬 목표 기준점. evolved 특성은 이 값을 사용하지 않는다.",
    )
    last_expressed: Optional[float] = Field(
        default=None,
        description="마지막으로 발현된 시각 (Unix timestamp). 감쇠 계산에 사용. 아직 발현 전이면 None.",
    )
    expression_count: int = Field(
        default=0,
        description="누적 발현 횟수. 성장 추적 및 향후 'evolved → core 승격' 규칙의 근거.",
    )


class Persona(BaseModel):
    """
    에이전트의 전체 정체성을 담는 상태 객체.

    구성:
        - 정체성 정보 (name, concept, tone, values): 사용자가 시드로 부여하며,
          이후 대화에서 거의 변하지 않는 정적 정보.
        - 성격의 실체 (traits): Trait들의 딕셔너리. 강화 루프가 매 턴마다
          갱신하는 동적 상태.
        - 진행 상태 (turn_count): 대화 누적 횟수. 성장 추적용.

    traits를 Dict[str, Trait]로 둔 이유:
        강화 루프가 "특정 이름의 특성을 찾아 강도를 갱신"하는 작업을
        매 턴 반복하므로, 이름 기반 O(1) 접근이 가능한 딕셔너리가 적합하다.
        키와 Trait.name은 항상 일치해야 한다.

    이 객체는 LLM에 직접 전달되지 않는다. 시스템 프롬프트는 매 턴
    이 Persona 상태로부터 생성되며, 강도 변화가 자연스럽게 프롬프트에
    반영된다.
    """

    name: str = Field(
        description=(
            "에이전트의 호칭. 사용자가 seed에서 명시한 이름을 그대로 쓴다. "
            "명시되지 않았다면 컨셉을 함축하는 짧은 이름(1-3 단어)을 만든다."
        )
    )
    concept: str = Field(
        description=(
            "에이전트가 어떤 존재인지를 한두 문장으로 요약한 컨셉. "
            "사용자의 seed text를 압축해 '이 에이전트가 누구인가'를 담는다. "
            "성격 특성은 traits에 따로 들어가므로 여기서는 정체성과 역할에 집중한다."
        )
    )
    tone: List[str] = Field(
        default_factory=list,
        description=(
            "말투를 묘사하는 키워드 목록 (2-5개 권장). "
            "예: ['간결한', '직설적인', '약간 냉소적인']. "
            "문장이 아닌 형용사 위주의 짧은 키워드로 적는다."
        ),
    )
    values: List[str] = Field(
        default_factory=list,
        description=(
            "에이전트가 중요하게 여기는 가치관 키워드 (1-5개). "
            "판단과 우선순위의 기준이 된다. 예: ['정직', '자유', '효율']. "
            "성격 특성(traits)이 '어떻게 말하느냐'라면, values는 '무엇을 옳다고 보느냐'다."
        ),
    )
    traits: Dict[str, Trait] = Field(
        default_factory=dict,
        description=(
            "에이전트의 성격 특성. 키는 특성 이름이고 값은 Trait 객체다. "
            "seed에서 추출된 특성은 모두 kind='core', strength=0.7, "
            "seed_strength=0.7로 시작한다. 키와 Trait.name은 항상 일치해야 한다."
        ),
    )
    turn_count: int = Field(
        default=0,
        description="누적 대화 턴 수. 새 페르소나는 0에서 시작한다.",
    )
