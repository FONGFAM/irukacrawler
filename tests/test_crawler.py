"""
tests/test_crawler.py — Unit test cho BaseCrawler (blacklist, dedup URL Cấp 2).

Không test I/O thật (không gọi internet), chỉ test logic nội bộ.
"""
import json
import os
import tempfile
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.crawlers.documentCrawlers import BaseCrawler


@pytest.fixture
def tmp_dir(tmp_path):
    """Tạo thư mục tạm cho output."""
    return str(tmp_path / "raw")


@pytest.fixture
def crawler(tmp_dir):
    return BaseCrawler(output_dir=tmp_dir)


class TestBlacklist:
    """Kiểm tra logic lọc domain trong blacklist."""

    @pytest.mark.asyncio
    async def test_blacklist_domain_tra_ve_none(self, crawler):
        result = await crawler.download_file("https://scribd.com/document/123")
        assert result is None

    @pytest.mark.asyncio
    async def test_blacklist_subdomain_tra_ve_none(self, crawler):
        result = await crawler.download_file("https://www.tailieu.vn/doc/giao-an.html")
        assert result is None

    @pytest.mark.asyncio
    async def test_domain_khong_trong_blacklist_duoc_tiep_tuc(self, crawler):
        """Domain hợp lệ phải được xử lý tiếp (test chỉ kiểm tra không bị block sớm)."""
        # Mock fetch để không gọi mạng thật
        crawler.fetch = AsyncMock(return_value=None)
        result = await crawler.download_file("https://moet.gov.vn/doc.pdf")
        # fetch được gọi → không bị block bởi blacklist
        crawler.fetch.assert_called_once()


class TestDedupURL:
    """Kiểm tra Dedup Cấp 2: bỏ qua URL đã cào thành công."""

    @pytest.mark.asyncio
    async def test_url_da_cao_bi_bo_qua(self, crawler):
        url = "https://example.com/already-crawled.pdf"
        crawler.crawled_urls.add(url)
        result = await crawler.download_file(url)
        assert result is None

    @pytest.mark.asyncio
    async def test_url_chua_cao_duoc_tiep_tuc(self, crawler):
        url = "https://example.com/new-doc.pdf"
        assert url not in crawler.crawled_urls
        # Mock để không gọi mạng thật
        crawler.fetch = AsyncMock(return_value=None)
        await crawler.download_file(url)
        crawler.fetch.assert_called_once()

    def test_crawled_urls_duoc_load_tu_file(self, tmp_dir):
        """Khi khởi tạo, crawler phải load danh sách URL từ file json (nếu có)."""
        urls = ["https://a.com/1.pdf", "https://b.com/2.pdf"]
        os.makedirs(tmp_dir, exist_ok=True)
        db_path = os.path.join(os.path.dirname(tmp_dir), "crawled_urls.json")
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(urls, f)

        crawler2 = BaseCrawler(output_dir=tmp_dir)
        assert "https://a.com/1.pdf" in crawler2.crawled_urls
        assert "https://b.com/2.pdf" in crawler2.crawled_urls

    def test_crawled_urls_duoc_luu_sau_download(self, crawler, tmp_dir):
        """Sau khi lưu file thành công, URL phải được thêm vào DB và persist."""
        url = "https://example.com/new.pdf"
        content = b"PDF content here " * 100  # > 0 bytes

        # Giả lập đã lưu file thành công
        import hashlib
        from pathlib import Path
        file_hash = hashlib.sha256(content).hexdigest()
        file_path = Path(tmp_dir) / f"{file_hash}.pdf"
        file_path.write_bytes(content)

        crawler.crawled_urls.add(url)
        crawler._save_crawled_urls()

        db_path = crawler.crawled_urls_file
        with open(db_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert url in saved


class TestDedupHash:
    """Kiểm tra Dedup Cấp 1: file đã tải (theo SHA-256 content)."""

    @pytest.mark.asyncio
    async def test_file_da_ton_tai_theo_hash_skip(self, crawler, tmp_dir):
        """Nếu file hash đã tồn tại trong thư mục → trả về đường dẫn cũ, không ghi đè."""
        import hashlib
        from pathlib import Path

        content = b"Duplicate PDF content " * 50
        file_hash = hashlib.sha256(content).hexdigest()
        file_path = Path(tmp_dir) / f"{file_hash}.pdf"
        file_path.write_bytes(content)

        # Mock fetch trả về content giống hệt
        crawler.fetch = AsyncMock(return_value=(content, ".pdf"))
        # Mock robots check
        crawler._check_robots = AsyncMock(return_value=True)
        crawler._rate_limit = AsyncMock()

        url = "https://example.com/dup.pdf"
        result = await crawler.download_file(url)

        assert result == str(file_path)
        # File không bị ghi lại
        assert file_path.stat().st_size == len(content)
