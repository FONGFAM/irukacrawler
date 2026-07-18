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
from src.searcher.queryExpander import expand_query
# pyrefly: ignore [missing-import]
from src.searcher.domainBlacklist import DomainBlacklist
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

async def run_pipeline(queries: List[str], provider: str, limit: int, semaphore: int = 5, query_offset: int = 0):
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
    
    # Khởi tạo DomainBlacklist (Hướng 3)
    domain_bl = DomainBlacklist(threshold=50)
    
    try:
        url_to_query = {}
        all_urls_raw = []
        # Bước 1: Gọi MCP Searcher lấy list URLs
        # Hướng 1: Mỗi query gốc được expand thành nhiều biến thể
        for query in queries:
            base_query = f"{query} site:youtube.com" if provider == "youtube" else query
            expanded_queries = expand_query(base_query, max_variants=4, offset=query_offset)
            for eq in expanded_queries:
                urls = await searcher.search(eq, limit=limit)
                for u in urls:
                    if u not in url_to_query:
                        url_to_query[u] = query
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

        # Hướng 3: Nạp DomainBlacklist từ manifest
        domain_bl.load_from_manifest(exporter.manifest_path)

        # Loại bỏ các URL trùng lặp (nếu có) hoặc đã từng cào / xử lý thành công
        deduped = [u for u in set(all_urls_raw) if u not in existing_urls and u not in crawler.crawled_urls]
        # Hướng 3: Lọc thêm các URL thuộc domain đã đủ quota
        all_urls = domain_bl.filter_urls(deduped)
        logger.info(f"Tổng số URL tìm được: {len(all_urls_raw)}, sau dedup: {len(deduped)}, cần tải (sau domain filter): {len(all_urls)}")

        async def process_url(url: str, original_query: str, sem: asyncio.Semaphore) -> str:
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
                
                # ── 4c. Thử lấy title từ HTML hoặc file MD nếu tên file là hash (không có ý nghĩa)
                real_title = None
                if len(doc_name) == 64 or doc_name.startswith("http"):
                    try:
                        real_title = await crawler.extract_page_title(url)
                        if real_title:
                            logger.info(f"Lấy được title từ HTML: '{real_title}'")
                    except Exception:
                        pass
                        
                    if not real_title and md_path:
                        try:
                            with open(md_path, "r", encoding="utf-8") as f:
                                for line in f:
                                    line_str = line.strip()
                                    if line_str.startswith("# ") or line_str.startswith("## "):
                                        title_candidate = line_str.lstrip("#").strip()
                                        if 10 <= len(title_candidate) <= 150:
                                            real_title = title_candidate
                                            logger.info(f"Lấy được title từ file MD: '{real_title}'")
                                            break
                        except Exception as e:
                            logger.warning(f"Không thể lấy title từ file MD: {e}")

                if real_title:
                    meta.name = real_title
                    # Re-run heuristic rules on the actual title
                    new_meta_dict = heuristic.apply_rules(name=real_title, url=url)
                    for k, v in new_meta_dict.items():
                        if v:
                            setattr(meta, k, v)
                
                # Đọc trước một đoạn để LLM xử lý
                with open(md_path, "r", encoding="utf-8") as f:
                    preview_text = f.read(2500)
                    
                # BƯỚC MỚI: Gatekeeper (Chấm điểm lọc rác)
                async with llm_sem:
                    logger.info(f"Đang chấm điểm Gatekeeper cho: {url}")
                    score = await llm_enricher.evaluate_relevance(preview_text, original_query, url=url)
                    
                if score < 35:
                    logger.warning(f"BỊ LOẠI (Gatekeeper Score = {score}/100): {url}")
                    return "FAILED"
                logger.success(f"PASS GATEKEEPER (Score = {score}/100): {url}")

                # Nếu chưa đủ 4 chiều, gọi Ollama LLM (Pass 2)
                if not meta.is_valid():
                    async with llm_sem:
                        llm_result = await llm_enricher.analyze_document(name=meta.name, url=url, preview=preview_text, user_query=original_query)
                        
                        if llm_result:
                            if llm_result.get("suggested_name"):
                                meta.name = llm_result.get("suggested_name")
                            linh_vucs_llm = llm_result.get("linh_vucs") or llm_result.get("linh_vuc")
                            if not meta.linh_vucs and linh_vucs_llm:
                                meta.linh_vucs = linh_vucs_llm
                            if not meta.age_bands and llm_result.get("age_bands"):
                                meta.age_bands = llm_result.get("age_bands")
                            if not meta.doc_type and llm_result.get("doc_type"):
                                meta.doc_type = llm_result.get("doc_type")
                            if not meta.source_tier and llm_result.get("source_tier"):
                                meta.source_tier = llm_result.get("source_tier")
                            if not meta.sub_domain_ids and llm_result.get("sub_domain_ids"):
                                meta.sub_domain_ids = llm_result.get("sub_domain_ids")
                            if llm_result.get("game_assets_potential"):
                                # Lưu game assets vào biến tạm hoặc metadata attributes
                                meta.game_assets_potential = llm_result.get("game_assets_potential")

                doc_dto = DocumentDTO(
                    metadata=meta,
                    raw_file_path=file_path,
                    converted_md_path=md_path
                )
                
                # Hard Drop: Nếu AI đã chấm là "Khác" (Rác/Lạc đề) thì vứt luôn, không bắt user duyệt
                if meta.doc_type == "khac":
                    logger.warning(f"AI phân loại là 'Khác' (Rác/Lạc đề), TỪ CHỐI TỰ ĐỘNG: {meta.name}")
                    return "FAILED"
                
                # BƯỚC MỚI: Mọi tài liệu hợp lệ sau khi tải và qua AI đều BẮT BUỘC phải qua tay người duyệt (need_manual = True)
                doc_dto.need_manual = True
                
                file_valid = validator.validate_file(md_path)
                if not file_valid:
                    logger.warning(f"File không hợp lệ: {doc_name}")
                    
                # Bước 6: Export Local (vào manifest.csv chờ duyệt)
                exporter.export(doc_dto)
                logger.warning(f"Đã đưa vào danh sách chờ duyệt tay: {meta.name}")
                return "MANUAL"

        # Thực thi song song tất cả URL
        results = await asyncio.gather(*(process_url(u, url_to_query[u], sem) for u in all_urls))
        success_count = results.count("SUCCESS")
        manual_count = results.count("MANUAL")
        fail_count = results.count("FAILED")

        import json
        stats = {
            "total_raw": len(all_urls_raw),
            "after_dedup": len(deduped),
            "after_domain_filter": len(all_urls),
            "success": success_count,
            "manual": manual_count,
            "failed_or_skipped": fail_count
        }
        print(f"===STATS=== {json.dumps(stats)}")
        
        logger.success(f"Hoàn thành Pipeline! Thành công: {success_count}, Cần duyệt: {manual_count}, Thất bại/Bỏ qua: {fail_count}")
    finally:
        await crawler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawler Tài liệu tham khảo IruKa (Local Standalone + MCP Search)")
    parser.add_argument("--queries", type=str, required=True, help="Các từ khóa tìm kiếm, cách nhau bằng dấu phẩy")
    parser.add_argument("--provider", type=str, default="tavily", choices=["tavily", "exa", "youtube"], help="Tavily, Exa, hoặc YouTube")
    parser.add_argument("--limit", type=int, default=5, help="Số kết quả trả về cho mỗi từ khóa")
    parser.add_argument("--semaphore", type=int, default=5, help="Số URL tải song song")
    parser.add_argument("--query-offset", type=int, default=0, help="Vị trí bắt đầu lấy biến thể câu truy vấn")
    
    args = parser.parse_args()
    
    query_list = [q.strip() for q in args.queries.split(",") if q.strip()]
    asyncio.run(run_pipeline(query_list, args.provider, args.limit, args.semaphore, args.query_offset))