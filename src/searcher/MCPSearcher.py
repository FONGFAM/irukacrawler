import os
import asyncio
from typing import List
# pyrefly: ignore [missing-import]
from loguru import logger
# pyrefly: ignore [missing-import]
from mcp.client.stdio import stdio_client, StdioServerParameters
# pyrefly: ignore [missing-import]
from mcp.client.session import ClientSession
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

class MCPSearcher:
    def __init__(self, provider: str = "tavily"):
        self.provider = provider.lower()
        if self.provider == "tavily":
            cmd_str = os.getenv("MCP_TAVILY_COMMAND", "npx,-y,@tavily/mcp-server")
        elif self.provider == "exa":
            cmd_str = os.getenv("MCP_EXA_COMMAND", "npx,-y,@exa/mcp-server")
        else:
            raise ValueError("Chỉ hỗ trợ 'tavily' hoặc 'exa'")
            
        parts = cmd_str.split(",")
        self.cmd = parts[0]
        self.args = parts[1:]

    async def search(self, query: str, limit: int = 10) -> List[str]:
        """Gọi MCP tool để tìm kiếm các URL."""
        logger.info(f"Bắt đầu tìm kiếm với {self.provider.upper()}: '{query}'")
        
        expanded_queries = [query]
        
        server_params = StdioServerParameters(
            command=self.cmd,
            args=self.args,
            env=os.environ.copy()
        )
        
        all_urls = set()
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for q in expanded_queries:
                        logger.info(f"-> Đang tìm nhánh: '{q}'")
                        if self.provider == "tavily":
                            tool_name = "tavily_search"
                            # Tavily tìm kiếm chung, thêm DOCX để quét rộng hơn
                            arguments = {"query": f"{q} (filetype:pdf OR filetype:doc OR filetype:docx)", "max_results": limit}
                        else:
                            # Exa search
                            tool_name = "web_search_exa"
                            arguments = {"query": q, "num_results": limit}

                        try:
                            result = await session.call_tool(tool_name, arguments=arguments)
                            
                            if result.content:
                                import json
                                import re
                                text_content = result.content[0].text
                                try:
                                    # Tùy theo cấu trúc trả về của từng MCP
                                    data = json.loads(text_content)
                                    
                                    # Phân tích kết quả của Tavily
                                    if isinstance(data, dict) and "results" in data:
                                        urls = [item.get("url") for item in data["results"] if item.get("url")]
                                        all_urls.update(urls)
                                    # Phân tích kết quả của Exa
                                    elif isinstance(data, list):
                                        urls = [item.get("url") for item in data if isinstance(item, dict) and item.get("url")]
                                        all_urls.update(urls)
                                    else:
                                        raise ValueError("Invalid JSON format")
                                except Exception:
                                    # Fallback: dùng Regex trích xuất toàn bộ URL từ text trả về
                                    found_urls = re.findall(r'https?://[^\s)"]+', text_content)
                                    if found_urls:
                                        all_urls.update(found_urls)
                        except Exception as e:
                            logger.error(f"Lỗi nhánh '{q}': {e}")
                            
        except Exception as e:
            logger.error(f"Lỗi khi chạy MCP Server ({self.provider}): {e}")
            
        logger.success(f"Tìm thấy tổng cộng {len(all_urls)} URLs qua {self.provider} (từ {len(expanded_queries)} nhánh tìm kiếm)")
        return list(all_urls)
