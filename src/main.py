import asyncio
import argparse
# pyrefly: ignore [missing-import]
from loguru import logger
from pathlib import Path
from typing import List
# pyrefly: ignore [missing-import]
from src.crawlers.documentCrawlers import BaseCrawler
# pyrefly: ignore [missing-import]
from src.crawlers.youtubeCrawler import YouTubeCrawler
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

async def run_pipeline(queries: List[str], provider: str, limit: int):
    # Khởi tạo các module
    searcher = MCPSearcher(provider=provider)
    crawler = BaseCrawler()
    youtube_crawler = YouTubeCrawler()
    converter = DocumentConverter()
    heuristic = HeuristicEnricher()
    llm_enricher = LocalLLMEnricher()
    validator = Validator()
    exporter = LocalExporter()

    logger.info(f"Bắt đầu pipeline tìm kiếm với {len(queries)} từ khóa...")
    
    try:
        all_urls = []
        # Bước 1: Gọi MCP Searcher lấy list URLs
        for query in queries:
            urls = await searcher.search(query, limit=limit)
            all_urls.extend(urls)
            
        # Loại bỏ các URL trùng lặp (nếu có)
        all_urls = list(set(all_urls))
        logger.info(f"Tổng số URL cần tải: {len(all_urls)}")

        for url in all_urls:
            # Phân luồng Youtube hoặc File thường
            if "youtube.com" in url or "youtu.be" in url:
                md_path = await youtube_crawler.download_file(url)
                if not md_path:
                    continue
                file_path = md_path # raw_file_path coi như là file md luôn
            else:
                # Bước 2: Tải file
                file_path = await crawler.download_file(url)  # Tự phát hiện định dạng
                if not file_path:
                    continue
                    
                # Bước 3: Chuyển sang MD
                md_path = converter.convert(file_path)
                if not md_path:
                    continue

            doc_name = Path(file_path).stem
            
            # Bước 4: Enrich Metadata (Heuristic)
            meta_dict = heuristic.apply_rules(name=doc_name, url=url)
            
            meta = DocumentMetadata(
                name=doc_name,
                source_url=url,
                **meta_dict
            )
            
            # Nếu chưa đủ 4 chiều, gọi Ollama LLM
            if not meta.is_valid():
                with open(md_path, "r", encoding="utf-8") as f:
                    preview_text = f.read(1000)
                    
                llm_result = llm_enricher.analyze_document(name=doc_name, url=url, preview=preview_text)
                if llm_result:
                    linh_vucs_llm = llm_result.get("linh_vucs") or llm_result.get("linh_vuc")
                    if not meta.linh_vucs and linh_vucs_llm:
                        meta.linh_vucs = linh_vucs_llm
                    if not meta.age_bands and llm_result.get("age_band"):
                        meta.age_bands = llm_result.get("age_band")
                    if not meta.doc_type and llm_result.get("doc_type"):
                        meta.doc_type = llm_result.get("doc_type")
                    if not meta.source_tier and llm_result.get("source_tier"):
                        meta.source_tier = llm_result.get("source_tier")

            # Bước 5: Validate
            doc_dto = DocumentDTO(
                metadata=meta,
                raw_file_path=file_path,
                converted_md_path=md_path
            )
            
            if not validator.validate_file(md_path) or not validator.validate_metadata(meta):
                doc_dto.need_manual = True
                
            # Bước 6: Export Local
            exporter.export(doc_dto)

        logger.success("Hoàn thành Pipeline Tìm kiếm & Tải tài liệu tự động (Local Mode)!")
    finally:
        await crawler.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawler Tài liệu tham khảo IruKa (Local Standalone + MCP Search)")
    parser.add_argument("--queries", type=str, required=True, help="Các từ khóa tìm kiếm, cách nhau bằng dấu phẩy")
    parser.add_argument("--provider", type=str, default="tavily", choices=["tavily", "exa"], help="Tavily hoặc Exa")
    parser.add_argument("--limit", type=int, default=5, help="Số kết quả trả về cho mỗi từ khóa")
    
    args = parser.parse_args()
    
    query_list = [q.strip() for q in args.queries.split(",") if q.strip()]
    asyncio.run(run_pipeline(query_list, args.provider, args.limit))
