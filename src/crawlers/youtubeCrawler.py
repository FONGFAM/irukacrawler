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
        from src.crawlers.titleCache import TitleCache
        self.title_cache = TitleCache()
        
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Lấy Video ID từ URL Youtube"""
        parsed = urlparse(url)
        if parsed.hostname in ['www.youtube.com', 'youtube.com']:
            return parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.hostname in ['youtu.be']:
            return parsed.path[1:]
        return None

    async def _get_video_title(self, url: str, video_id: Optional[str] = None) -> str:
        """Cào HTML của trang YouTube để lấy thẻ <title> hoặc đọc từ Cache"""
        if not video_id:
            video_id = self._extract_video_id(url)
        if video_id:
            cached = self.title_cache.get(video_id)
            if cached:
                return cached
                
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.text.replace("- YouTube", "").strip()
                    # Xoá các ký tự không hợp lệ cho file
                    title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
                    if title:
                        if video_id:
                            self.title_cache.set(video_id, title)
                        return title
        except Exception as e:
            logger.warning(f"Không thể lấy tiêu đề từ {url}: {e}")
            
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    # Các từ khóa ngoài phạm vi (Luôn luôn loại bỏ)
    TITLE_POISON_HARD = [
        "lớp 2", "lớp 3", "lớp 4", "lớp 5", "lớp 6", "lớp 7", "lớp 8", "lớp 9", "lớp 10", "lớp 11", "lớp 12",
        "tiếng việt 2", "tiếng việt 3", "tiếng việt 4", "tiếng việt 5",
        "toán 2", "toán 3", "toán 4", "toán 5",
        "mỹ thuật 6", "ngữ văn 6", "lịch sử 6",
        "thcs", "thpt", "trung học", "đại học", "cao đẳng",
        "grade 2", "grade 3", "grade 4", "grade 5",
    ]

    # Các từ khóa lớp 1 / tiểu học chung chung (Sẽ loại bỏ trừ khi có từ khóa whitelist đi kèm)
    TITLE_POISON_SOFT = [
        "lớp 1", "tiếng việt 1", "toán 1", "grade 1", "tiểu học"
    ]

    # Các từ khóa khẳng định mầm non hoặc học kỳ lớp 1 hợp lệ
    TITLE_WHITELIST = [
        "mầm non", "mẫu giáo", "nhà trẻ", "lớp mầm", "lớp chồi", "lớp lá",
        "3-4 tuổi", "4-5 tuổi", "5-6 tuổi", "trẻ 3 tuổi", "trẻ 4 tuổi", "trẻ 5 tuổi",
        "học kỳ 1", "học kỳ 2", "hk1", "hk2", "hk 1", "hk 2", "hki", "hkii",
        "lớp 1 học kỳ", "lớp 1 hk", "lớp một học kỳ"
    ]

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
            title = await self._get_video_title(url, video_id)
            
            # ── PRE-FILTER: Kiểm tra tiêu đề TRƯỚC khi tải transcript ──
            from src.enricher.heuristicEnricher import remove_accents
            title_lower = remove_accents(title.lower())
            
            # 1. HARD POISON check: Luôn luôn loại bỏ
            for kw in self.TITLE_POISON_HARD:
                kw_norm = remove_accents(kw.lower())
                if kw_norm in title_lower:
                    logger.warning(f"Bỏ qua video ngoài mầm non (HARD poison: {kw}): {title}")
                    return None
                    
            # 2. WHITELIST check: Nếu khớp -> bypass SOFT POISON check
            is_whitelisted = any(remove_accents(kw.lower()) in title_lower for kw in self.TITLE_WHITELIST)
            
            if not is_whitelisted:
                # 3. SOFT POISON check: Loại bỏ nếu không có context mầm non/học kỳ đi kèm
                for kw in self.TITLE_POISON_SOFT:
                    kw_norm = remove_accents(kw.lower())
                    if kw_norm in title_lower:
                        logger.warning(f"Bỏ qua video lớp 1/tiểu học chung chung (SOFT poison: {kw}): {title}")
                        return None
            
            logger.info(f"Đang cào Transcript cho video: {title} ({video_id})...")
            
            # v1.x dùng instance, không gọi static
            api = YouTubeTranscriptApi()
            
            # Lấy danh sách phụ đề
            transcript_list = api.list(video_id)
            
            try:
                # Ưu tiên phụ đề tiếng Việt (thủ công hoặc tự động)
                transcript_obj = transcript_list.find_transcript(['vi'])
            except Exception:
                # Không có tiếng Việt → lấy cái đầu tiên rồi dịch
                transcripts_available = list(transcript_list)
                if not transcripts_available:
                    raise Exception("Video không có bất kỳ phụ đề nào.")
                transcript_obj = transcripts_available[0].translate('vi')

            # v1.x: fetch() trả về FetchedTranscript, dùng .to_raw_data() lấy list dict
            fetched = transcript_obj.fetch()
            raw_data = fetched.to_raw_data()  # list of {'text': ..., 'start': ..., 'duration': ...}
            full_text = " ".join(item['text'] for item in raw_data)
            
            # Đảm bảo tên file an toàn
            safe_title = title[:150]  # Tránh tên file quá dài
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
            err_msg = str(e)
            if "Subtitles are disabled" in err_msg or "Could not retrieve a transcript" in err_msg:
                logger.warning(f"Video không có phụ đề: {url}")
            else:
                logger.error(f"Lỗi khi cào transcript YouTube {url}: {err_msg}")
            return None
