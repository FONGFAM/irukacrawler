from typing import Optional
from urllib.parse import urlparse, parse_qs
# pyrefly: ignore [missing-import]
from loguru import logger
import hashlib
from pathlib import Path

try:
    # pyrefly: ignore [missing-import]
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

class YouTubeCrawler:
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Lấy Video ID từ URL Youtube"""
        parsed = urlparse(url)
        if parsed.hostname in ['www.youtube.com', 'youtube.com']:
            return parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.hostname in ['youtu.be']:
            return parsed.path[1:]
        return None

    async def download_file(self, url: str) -> Optional[str]:
        """Cào Transcript của video YouTube thay vì tải video"""
        if YouTubeTranscriptApi is None:
            logger.error("Cần cài đặt youtube-transcript-api: pip install youtube-transcript-api")
            return None
            
        video_id = self._extract_video_id(url)
        if not video_id:
            logger.warning(f"Không tìm thấy Video ID hợp lệ từ URL: {url}")
            return None
            
        try:
            logger.info(f"Đang cào Transcript cho video {video_id}...")
            # Lấy transcript tiếng Việt hoặc tự động dịch sang tiếng Việt
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['vi'])
            
            # Nối text lại
            full_text = " ".join([t['text'] for t in transcript])
            
            # Lưu file markdown (coi như raw text)
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
            file_path = self.output_dir / f"{url_hash}.md"
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# YouTube Transcript\nURL: {url}\n\n{full_text}")
                
            logger.info(f"Tải transcript thành công: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Lỗi khi cào transcript YouTube {url}: {e}")
            return None
