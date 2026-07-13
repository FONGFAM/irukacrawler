import json
from pathlib import Path
from typing import Optional
from loguru import logger

class TitleCache:
    def __init__(self, cache_file: str = "data/.cache_titles.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache = {}
        self.load()

    def load(self) -> None:
        if self.cache_file.exists() and self.cache_file.stat().st_size > 0:
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning(f"TitleCache: Không thể đọc cache: {e}")

    def save(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"TitleCache: Không thể ghi cache: {e}")

    def get(self, video_id: str) -> Optional[str]:
        return self._cache.get(video_id)

    def set(self, video_id: str, title: str) -> None:
        if video_id and title:
            self._cache[video_id] = title
            self.save()
