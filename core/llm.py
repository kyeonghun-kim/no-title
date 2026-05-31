# core/llm.py

from typing import Dict, Any
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from dotenv import load_dotenv

load_dotenv()

ROLE_CONFIG: Dict[str, Any] = {
    "main": {"model": "openai:gpt-5.5"},
    "extract": {"model": "openai:gpt-5-mini"},
    "reflect": {"model": "openai:gpt-5.5"},
}


def get_llm(role: str = "main") -> BaseChatModel:
    """
    role에 매핑된 LLM 인스턴스를 반환한다.

    호출자는 "어떤 모델/provider를 쓸지" 알 필요 없이 role(용도)만 지정한다.
    실제 모델 선택은 ROLE_CONFIG가 책임진다.

    Args:
        role: 사용 용도. ROLE_CONFIG에 정의된 키 중 하나
              ("main": 사용자 대화용,
               "extract": seed → Persona 추출용,
               "reflect": 대화 → 발현 특성 분석용).

    Returns:
        해당 role에 매핑된 LangChain BaseChatModel 인스턴스.

    Raises:
        ValueError: ROLE_CONFIG에 없는 role이 주어진 경우.
    """
    if role not in ROLE_CONFIG:
        raise ValueError(f"Unknown role: {role!r}. Available: {list(ROLE_CONFIG)}")

    cfg = ROLE_CONFIG[role]

    return init_chat_model(**cfg)
