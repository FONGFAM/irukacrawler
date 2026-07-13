"""
DomainBlacklist: Theo dõi và loại bỏ các domain đã được cào đủ số lượng.

Cách hoạt động:
  - Đọc manifest.csv, đếm số tài liệu thành công từ mỗi domain
  - Nếu một domain đã đóng góp >= threshold tài liệu → đưa vào blacklist
  - Bộ lọc URL áp dụng danh sách này để loại bỏ trước khi xử lý
"""

from urllib.parse import urlparse
from typing import Set, List
from pathlib import Path
# pyrefly: ignore [missing-import]
from loguru import logger


class DomainBlacklist:
    def __init__(self, threshold: int = 5):
        """
        Args:
            threshold: Số tài liệu tối đa thu thập từ 1 domain.
                       Vượt ngưỡng → domain bị đưa vào blacklist.
        """
        self.threshold = threshold
        self._blacklisted: Set[str] = set()
        self._domain_counts: dict = {}

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            # Bỏ www. để gộp www.example.com và example.com
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def load_from_manifest(self, manifest_path: Path) -> None:
        """Đọc manifest.csv và cập nhật domain_counts + blacklist."""
        if not manifest_path.exists() or manifest_path.stat().st_size == 0:
            return
        try:
            import csv
            self._domain_counts = {}
            with open(manifest_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Chỉ đếm tài liệu không phải KHAC và không cần duyệt tay
                    if row.get("need_manual", "0") == "1":
                        continue
                    url = row.get("source_url", "")
                    domain = self._extract_domain(url)
                    if domain:
                        self._domain_counts[domain] = self._domain_counts.get(domain, 0) + 1

            # Cập nhật blacklist
            self._blacklisted = {
                d for d, count in self._domain_counts.items()
                if count >= self.threshold
            }
            if self._blacklisted:
                logger.info(f"DomainBlacklist: {len(self._blacklisted)} domain bị hạn chế (≥{self.threshold} tài liệu): {self._blacklisted}")
        except Exception as e:
            logger.warning(f"DomainBlacklist: Không thể đọc manifest: {e}")

    def is_blacklisted(self, url: str) -> bool:
        """Trả về True nếu URL thuộc domain đã bị blacklist."""
        domain = self._extract_domain(url)
        return domain in self._blacklisted

    def filter_urls(self, urls: List[str]) -> List[str]:
        """Lọc bỏ các URL thuộc domain bị blacklist."""
        filtered = []
        skipped = []
        for url in urls:
            if self.is_blacklisted(url):
                skipped.append(self._extract_domain(url))
            else:
                filtered.append(url)
        if skipped:
            logger.info(f"DomainBlacklist: Bỏ qua {len(skipped)} URLs từ domain đã đủ quota: {set(skipped)}")
        return filtered

    def get_domain_counts(self) -> dict:
        return dict(sorted(self._domain_counts.items(), key=lambda x: -x[1]))
