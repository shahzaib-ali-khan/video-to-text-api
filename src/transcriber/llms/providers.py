import logging
from typing import List, Type

from .assembly_ai import AssemblyTranscriberLLM
from .base import TranscriberLLM
from .open_ai import OpenAITranscriberLLM

logger = logging.getLogger(__name__)


ALL_PROVIDERS: List[Type[TranscriberLLM]] = [
    OpenAITranscriberLLM,
    AssemblyTranscriberLLM,
]


def get_available_transcribers(video_path: str) -> List[TranscriberLLM]:
    """
    Instantiate only providers that have API keys configured.
    Skip and log others.
    """
    available = []

    for provider_cls in ALL_PROVIDERS:
        if not provider_cls.is_configured():
            continue

        try:
            provider = provider_cls(video_path)
            available.append(provider)
        except ValueError as e:
            logger.warning(str(e))

    return available
