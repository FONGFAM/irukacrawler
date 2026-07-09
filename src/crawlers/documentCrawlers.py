"""
BaseCrawler — tải file an toàn từ danh sách URL.
Hỗ trợ: PDF, DOCX, HTML
Tuân thủ: robots.txt, Rate limit (1 req/sec), Dedup (SHA-256)
"""
import asyncio
import hashlib
import json
import urllib.robotparser
from pathlib import Path
from typing import Optional
# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
# pyrefly: ignore [missing-import]
from loguru import logger
from urllib.parse import urlparse
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()


USER_AGENT = os.getenv("USER_AGENT", "IruKa-Educational-Crawler/1.0 (contact: mr.dao@irukaedu.vn)")
MAX_REQUESTS_PER_SECOND = float(os.getenv("MAX_REQUESTS_PER_SECOND", "1.0"))

# Map content-type / đuôi file ra phần mở rộng chuẩn
EXT_MAP = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/html": ".html",
}

class BaseCrawler:
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Cache robots.txt theo domain
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self.last_request_time: dict[str, float] = {}  # per-domain rate limit
        self.blacklist = ["scribd.com", "docgo.net", "123docz.net", "tailieu.vn", "violet.vn"]

        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
            follow_redirects=True
        )

        # File DB lưu các URL đã tải thành công (Dedup Cấp 2)
        self.crawled_urls_file = self.output_dir.parent / "crawled_urls.json"
        self.crawled_urls: set = set()
        if self.crawled_urls_file.exists():
            try:
                with open(self.crawled_urls_file, "r", encoding="utf-8") as f:
                    self.crawled_urls = set(json.load(f))
            except Exception as e:
                logger.warning(f"Lỗi khi đọc file crawled_urls.json: {e}")


    # ─────────────────────────────────────────────
    # robots.txt check (với cache theo domain)
    # ─────────────────────────────────────────────
    async def _check_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self._robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            try:
                resp = await self.client.get(f"{domain}/robots.txt")
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
            except Exception as e:
                logger.warning(f"Không lấy được robots.txt từ {domain}: {e}")
            self._robots_cache[domain] = rp
        return self._robots_cache[domain].can_fetch(USER_AGENT, url)
    # ─────────────────────────────────────────────
    # Rate limit theo domain
    # ─────────────────────────────────────────────
    async def _rate_limit(self, domain: str):
        now = asyncio.get_event_loop().time()
        last = self.last_request_time.get(domain, 0.0)
        interval = 1.0 / MAX_REQUESTS_PER_SECOND
        wait = interval - (now - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self.last_request_time[domain] = asyncio.get_event_loop().time()

    # ─────────────────────────────────────────────
    # Lấy nội dung từ URL
    # ─────────────────────────────────────────────
    async def fetch(self, url: str) -> Optional[tuple[bytes, str]]:
        """Trả về (content_bytes, extension) hoặc None nếu lỗi."""
        if not await self._check_robots(url):
            logger.error(f"robots.txt từ chối: {url}")
            return None

        domain = urlparse(url).netloc
        await self._rate_limit(domain)

        try:
            logger.info(f"Đang tải: {url}")
            resp = await self.client.get(url)
            resp.raise_for_status()

            # Xác định đuôi file
            content_type = resp.headers.get("content-type", "").split(";")[0].strip()
            ext = EXT_MAP.get(content_type)
            if not ext:
                # Thử đoán từ URL path
                url_path = urlparse(url).path.lower()
                for e in [".pdf", ".docx", ".doc", ".html"]:
                    if url_path.endswith(e):
                        ext = e
                        break
                else:
                    ext = ".html"  # fallback

            return resp.content, ext

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} khi tải {url}")
        except Exception as e:
            logger.error(f"Lỗi khi tải {url}: {e}")

        return None

    # ─────────────────────────────────────────────
    # Tải và lưu file (dedup bằng SHA-256)
    # ─────────────────────────────────────────────
    async def download_file(self, url: str) -> Optional[str]:
        # 1. Kiểm tra Blacklist
        parsed = urlparse(url)
        domain = parsed.netloc
        if any(bl_domain in domain for bl_domain in self.blacklist):
            logger.warning(f"Bỏ qua URL vì nằm trong blacklist: {url}")
            return None

        """Tải file, tự nhận diện định dạng, Dedup bằng hash. Trả về đường dẫn local."""
        result = await self.fetch(url)
        if not result:
            return None

        content, ext = result
        file_hash = hashlib.sha256(content).hexdigest()
        file_path = self.output_dir / f"{file_hash}{ext}"

        if file_path.exists():
            logger.info(f"File đã có (Dedup): {file_path}")
            return str(file_path)

        with open(file_path, "wb") as f:
            f.write(content)

        # Cập nhật danh sách URL đã cào thành công
        self.crawled_urls.add(url)
        self._save_crawled_urls()

        logger.success(f"Đã lưu: {file_path}")
        return str(file_path)

    def _save_crawled_urls(self):
        """Ghi danh sách URL đã cào vào file JSON để dedup lần chạy sau."""
        try:
            with open(self.crawled_urls_file, "w", encoding="utf-8") as f:
                json.dump(list(self.crawled_urls), f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.warning(f"Lỗi khi lưu crawled_urls.json: {e}")

    # ─────────────────────────────────────────────
    # Lấy tiêu đề trang từ HTML (giúp Heuristic phân loại tốt hơn)
    # ─────────────────────────────────────────────
    async def extract_page_title(self, url: str, content: Optional[bytes] = None) -> Optional[str]:
        """Lấy tiêu đề trang web từ thẻ <title> để enrich metadata.
        
        Args:
            url: URL của trang.
            content: Nội dung HTML đã tải (nếu có), nếu None sẽ tự tải.
            
        Returns:
            Tiêu đề trang hoặc None nếu không lấy được.
        """
        if content is None:
            result = await self.fetch(url)
            if not result:
                return None
            content, ext = result
            if ext != ".html":
                return None  # Chỉ xử lý HTML
        
        try:
            soup = BeautifulSoup(content.decode("utf-8", errors="ignore"), 'html.parser')
            title_tag = soup.find('title')
            if title_tag and title_tag.text.strip():
                title = title_tag.text.strip()
                # Cắt bớt tên site ở cuối (VD: "... - Mamnon.com" → "...")
                for suffix in [" - YouTube", " | Mamnon.com", " - Giaovienmamnon", " | Hoc10", " - Bộ GD&ĐT"]:
                    if title.lower().endswith(suffix.lower()):
                        title = title[:-len(suffix)]
                return title.strip()
        except Exception as e:
            logger.debug(f"Không parse được title từ {url}: {e}")
        
        return None

    async def close(self):
        await self.client.aclose()