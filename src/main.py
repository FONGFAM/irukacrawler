import asyncio
import argparse
# pyrefly: ignore [missing-import]
from loguru import logger
from pathlib import Path
from typing import List
from datetime import datetime
# pyrefly: ignore [missing-import]
from src.crawlers.documentCrawlers import BaseCrawler
# pyrefly: ignore [missing-import]
from src.crawlers.youtubeCrawler import YouTubeCrawler
# pyrefly: ignore [missing-import]
from src.crawlers.siteMetadataMapper import get_metadata_override, get_site_name
# pyrefly: ignore [missing-import]
from src.searcher.MCPSearcher import MCPSearcher
# pyrefly: ignore [missing-import]
from src.converters.documentConverter import DocumentConverter
# pyrefly: ignore [missing-import]
from src.enricher.heuristicEnricher import HeuristicEnricher
# pyrefly: ignore [missing-import]
from src.enricher.localLLMEnricher import LocalLLMEnricher
# pyrefly: ignore [missing-import]
from src.enricher.validator import Validator
# pyrefly: ignore [missing-import]
from src.exporter.LocalExporter import LocalExporter
# pyrefly: ignore [missing-import]
from src.models import DocumentDTO, DocumentMetadata

# Cấu hình log file ghi lại nhật ký truy cập/chạy của crawler
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)
log_file_path = logs_dir / f"crawler_{datetime.now().strftime('%Y-%m-%d')}.log"
logger.add(log_file_path, rotation="10 MB", retention="7 days", encoding="utf-8", level="DEBUG")

async def run_pipeline(queries: List[str], provider: str, limit: int, semaphore: int = 5):
    # Khởi tạo các module
    actual_provider = "exa" if provider == "youtube" else provider
    searcher = MCPSearcher(provider=actual_provider)
    crawler = BaseCrawler()
    youtube_crawler = YouTubeCrawler()
    converter = DocumentConverter()
    heuristic = HeuristicEnricher()
    llm_enricher = LocalLLMEnricher()
    validator = Validator()
    exporter = LocalExporter()

    logger.info(f"Bắt đầu pipeline tìm kiếm với {len(queries)} từ khóa...")
    sem = asyncio.Semaphore(semaphore)
    llm_sem = asyncio.Semaphore(1)  # Giới hạn LLM chạy tuần tự để tránh quá tải RAM/GPU
    success_count = 0
    fail_count = 0
    
    try:
        all_urls_raw = []
        # Bước 1: Gọi MCP Searcher lấy list URLs
        for query in queries:
            actual_query = f"{query} site:youtube.com" if provider == "youtube" else query
            urls = await searcher.search(actual_query, limit=limit)
            all_urls_raw.extend(urls)
            
        import pandas as pd
        existing_urls = set()
        if exporter.manifest_path.exists() and exporter.manifest_path.stat().st_size > 0:
            try:
                df = pd.read_csv(exporter.manifest_path)
                if "source_url" in df.columns:
                    existing_urls = set(df["source_url"].dropna().tolist())
            except Exception:
                pass
                
        # Loại bỏ các URL trùng lặp (nếu có) hoặc đã từng cào / xử lý thành công
        all_urls = [u for u in set(all_urls_raw) if u not in existing_urls and u not in crawler.crawled_urls]
        logger.info(f"Tổng số URL tìm được: {len(all_urls_raw)}, cần tải (sau khi lọc trùng): {len(all_urls)}")

        async def process_url(url: str, sem: asyncio.Semaphore) -> str:
            async with sem:
                # ── 0. Early Filter: Bỏ qua URL rõ ràng ngoài mầm non
                url_lower = url.lower()
                out_of_scope_kws = ["lop-2", "lop-3", "lop-4", "lop-5", "lop-6", "lop-7", "lop-8", "lop-9", "lop-10", "lop-11", "lop-12", "thcs", "thpt", "dai-hoc"]
                if any(kw in url_lower for kw in out_of_scope_kws):
                    logger.warning(f"Bỏ qua URL ngoài mầm non: {url}")
                    return "FAILED"
                    
                # Phân luồng Youtube hoặc File thường
                if "youtube.com" in url or "youtu.be" in url:
                    md_path = await youtube_crawler.download_file(url)
                    if not md_path:
                        return "FAILED"
                    file_path = md_path  # raw_file_path coi như là file md luôn
                else:
                    # Bước 2: Tải file
                    file_path = await crawler.download_file(url)  # Tự phát hiện định dạng
                    if not file_path:
                        return "FAILED"
                        
                    # Bước 3: Chuyển sang MD
                    md_path = converter.convert(file_path)
                    if not md_path:
                        return "FAILED"

                doc_name = Path(file_path).stem
                
                # Bước 4: Enrich Metadata (Heuristic)
                meta_dict = heuristic.apply_rules(name=doc_name, url=url)
                
                # ── 4b. Site Metadata Override (nếu URL thuộc domain đã biết)
                site_override = get_metadata_override(url)
                if site_override:
                    site_name = get_site_name(url) or url
                    logger.info(f"Áp dụng site metadata từ {site_name}: {site_override}")
                    # Ghi đè source_tier nếu site override có
                    if "source_tier" in site_override:
                        meta_dict["source_tier"] = site_override["source_tier"]
                    # Ghi đè doc_type nếu site override có và heuristic chưa gán
                    if "doc_type" in site_override and not meta_dict.get("doc_type"):
                        meta_dict["doc_type"] = site_override["doc_type"]
                
                meta = DocumentMetadata(
                    name=doc_name,
                    source_url=url,
                    **meta_dict
                )
                
                # ── 4c. Thử lấy title từ HTML nếu tên file là hash (không có ý nghĩa)
                if len(doc_name) == 64 or doc_name.startswith("http"):
                    try:
                        html_title = await crawler.extract_page_title(url)
                        if html_title:
                            logger.info(f"Lấy được title từ HTML: '{html_title}'")
                            meta.name = html_title
                    except Exception:
                        pass
                
                # Nếu chưa đủ 4 chiều, gọi Ollama LLM
                if not meta.is_valid():
                    with open(md_path, "r", encoding="utf-8") as f:
                        preview_text = f.read(1200)
                        
                    async with llm_sem:
                        llm_result = await llm_enricher.analyze_document(name=doc_name, url=url, preview=preview_text)
                        
                    if llm_result:
                        linh_vucs_llm = llm_result.get("linh_vucs") or llm_result.get("linh_vuc")
                        if not meta.linh_vucs and linh_vucs_llm:
                            meta.linh_vucs = linh_vucs_llm
                        if not meta.age_bands and llm_result.get("age_bands"):
                            meta.age_bands = llm_result.get("age_bands")
                        if not meta.doc_type and llm_result.get("doc_type"):
                            meta.doc_type = llm_result.get("doc_type")
                        if not meta.source_tier and llm_result.get("source_tier"):
                            meta.source_tier = llm_result.get("source_tier")

                doc_dto = DocumentDTO(
                    metadata=meta,
                    raw_file_path=file_path,
                    converted_md_path=md_path
                )
                
                # Bước 5: Validate & Đánh dấu duyệt tay
                # Luôn gọi validate_file + validate_metadata để làm sạch metadata,
                # ngay cả khi doc_type == "khac" (sửa lỗi: trước đây skip validate_metadata khi "khac")
                file_valid = validator.validate_file(md_path)
                meta_valid = validator.validate_metadata(meta)
                
                if meta.doc_type == "khac" or not file_valid or not meta_valid:
                    doc_dto.need_manual = True
                    if meta.doc_type == "khac":
                        logger.warning(f"Tài liệu phân loại 'khac', chuyển duyệt tay: {doc_name}")
                    
                # Bước 6: Export Local
                exporter.export(doc_dto)
                if doc_dto.need_manual:
                    logger.warning(f"Cần duyệt tay: {doc_name}")
                    return "MANUAL"
                else:
                    logger.success(f"Export thành công: {doc_name}")
                    return "SUCCESS"

        # Thực thi song song tất cả URL
        results = await asyncio.gather(*(process_url(u, sem) for u in all_urls))
        success_count = results.count("SUCCESS")
        manual_count = results.count("MANUAL")
        fail_count = results.count("FAILED")

        import json
        stats = {
            "total_searched": len(all_urls_raw),
            "deduplicated": len(all_urls_raw) - len(all_urls),
            "success": success_count,
            "manual": manual_count,
            "failed": fail_count
        }
        print(f"===STATS=== {json.dumps(stats)}")
        
        logger.success(f"Hoàn thành Pipeline! Thành công: {success_count}, Cần duyệt: {manual_count}, Thất bại/Bỏ qua: {fail_count}")
    finally:
        await crawler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawler Tài liệu tham khảo IruKa (Local Standalone + MCP Search)")
    parser.add_argument("--queries", type=str, required=True, help="Các từ khóa tìm kiếm, cách nhau bằng dấu phẩy")
    parser.add_argument("--provider", type=str, default="tavily", choices=["tavily", "exa"], help="Tavily hoặc Exa")
    parser.add_argument("--limit", type=int, default=5, help="Số kết quả trả về cho mỗi từ khóa")
    parser.add_argument("--semaphore", type=int, default=5, help="Số URL tải song song")
    
    args = parser.parse_args()
    
    query_list = [q.strip() for q in args.queries.split(",") if q.strip()]
    asyncio.run(run_pipeline(query_list, args.provider, args.limit, args.semaphore))