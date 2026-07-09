from typing import Optional
from urllib.parse import urlparse, parse_qs
# pyrefly: ignore [missing-import]
from loguru import logger
import hashlib
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
import re

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

    async def _get_video_title(self, url: str) -> str:
        """Cào HTML của trang YouTube để lấy thẻ <title>"""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.text.replace("- YouTube", "").strip()
                    # Xoá các ký tự không hợp lệ cho file
                    title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
                    return title if title else hashlib.sha256(url.encode()).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Không thể lấy tiêu đề từ {url}: {e}")
            
        return hashlib.sha256(url.encode()).hexdigest()[:16]

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
            title = await self._get_video_title(url)
            logger.info(f"Đang cào Transcript cho video: {title} ({video_id})...")
            
            # Lấy danh sách phụ đề
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            try:
                # Ưu tiên lấy phụ đề tiếng Việt nếu có (thủ công hoặc tự động)
                transcript_obj = transcript_list.find_transcript(['vi'])
            except:
                # Nếu không có tiếng Việt, lấy cái đầu tiên tìm được và tự động dịch sang tiếng Việt
                transcripts_available = list(transcript_list)
                if not transcripts_available:
                    raise Exception("Video không có bất kỳ phụ đề nào.")
                transcript_obj = transcripts_available[0].translate('vi')
                
            transcript_data = transcript_obj.fetch()
            
            # Nối text lại
            full_text = " ".join([t['text'] for t in transcript_data])
            
            # Đảm bảo tên file an toàn
            safe_title = title[:150] # Tránh tên file quá dài
            file_path = self.output_dir / f"{safe_title}.md"
            
            # Chống trùng lặp tên file
            counter = 1
            while file_path.exists():
                file_path = self.output_dir / f"{safe_title} ({counter}).md"
                counter += 1
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\nURL: {url}\n\n{full_text}")
                
            logger.info(f"Tải transcript thành công: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Lỗi khi cào transcript YouTube {url}: {e}")
            return None
