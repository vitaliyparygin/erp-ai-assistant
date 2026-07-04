
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class LLMService:
    def __init__(self):
        settings = get_settings()
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_model

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            logger.debug(
                "PROMPT_DEBUG",
                prompt=prompt[:3000]
            )
            response.raise_for_status()

            data = response.json()

            return data["response"]
