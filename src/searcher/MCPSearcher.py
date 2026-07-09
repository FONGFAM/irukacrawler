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
        """Gọi MCP tool để tìm kiếm các URL chứa tài liệu PDF/DOCX."""
        logger.info(f"Bắt đầu tìm kiếm với {self.provider.upper()}: '{query}'")
        server_params = StdioServerParameters(
            command=self.cmd,
            args=self.args,
            env=os.environ.copy()
        )
        
        urls = []
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    if self.provider == "tavily":
                        tool_name = "tavily_search"
                        # Tavily tìm kiếm chung
                        arguments = {"query": query + " filetype:pdf OR filetype:doc", "max_results": limit}
                    else:
                        # Exa search
                        tool_name = "web_search_exa"
                        arguments = {"query": query, "num_results": limit}

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
                            # Phân tích kết quả của Exa
                            elif isinstance(data, list):
                                urls = [item.get("url") for item in data if isinstance(item, dict) and item.get("url")]
                            else:
                                logger.warning("Dữ liệu JSON không chứa cấu trúc mong muốn. Fallback sang Regex...")
                                raise ValueError("Invalid JSON format")
                        except Exception as e:
                            logger.info(f"Không thể parse JSON từ MCP (lý do: {e}). Đang dùng Regex để bóc tách URL từ chuỗi text...")
                            # Fallback: dùng Regex trích xuất toàn bộ URL từ text trả về
                            found_urls = re.findall(r'https?://[^\s)"]+', text_content)
                            if found_urls:
                                urls = list(set(found_urls))
                            else:
                                logger.error(f"Không tìm thấy URL nào trong nội dung trả về: {text_content[:200]}")
                            
        except Exception as e:
            logger.error(f"Lỗi khi chạy MCP Server ({self.provider}): {e}")
            
        logger.success(f"Tìm thấy {len(urls)} URLs qua {self.provider}")
        return urls
