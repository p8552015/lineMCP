#!/usr/bin/env python3
"""
MCP 文件搜尋工具
整合 SQLite MCP server 提供智能文件搜尋功能
用於 GitHub Actions 錯誤診斷中的相關文件查找
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
import aiohttp
import traceback

# 添加專案路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'bot'))

try:
    from src.services.unified_mcp_client import UnifiedMCPClient
    from src.config.mcp_config import MCPConfig
except ImportError as e:
    logging.warning(f"無法導入 MCP 客戶端: {e}")
    UnifiedMCPClient = None
    MCPConfig = None

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜尋結果數據結構"""
    file_path: str
    content_snippet: str
    relevance_score: float
    match_type: str  # 'filename', 'content', 'pattern'
    line_number: Optional[int] = None
    context_lines: Optional[List[str]] = None


@dataclass
class SearchQuery:
    """搜尋查詢數據結構"""
    pattern: str
    search_type: str  # 'filename', 'content', 'both'
    file_extensions: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    max_results: int = 20
    include_context: bool = True


class MCPFileSearcher:
    """MCP 文件搜尋器"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:3003"):
        self.mcp_server_url = mcp_server_url
        self.mcp_client = None
        self.session = None
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """初始化 MCP 客戶端"""
        try:
            if UnifiedMCPClient:
                # 使用統一 MCP 客戶端
                self.mcp_client = UnifiedMCPClient()
                await self.mcp_client.initialize()
                self.is_initialized = True
                logger.info("MCP 客戶端初始化成功")
                return True
            else:
                # 降級到 HTTP 客戶端
                self.session = aiohttp.ClientSession()
                # 測試連接
                async with self.session.get(f"{self.mcp_server_url}/health", timeout=5) as response:
                    if response.status == 200:
                        self.is_initialized = True
                        logger.info("MCP HTTP 客戶端初始化成功")
                        return True
                    else:
                        logger.error(f"MCP 服務器響應錯誤: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"MCP 客戶端初始化失敗: {e}")
            return False
    
    async def cleanup(self):
        """清理資源"""
        if self.mcp_client:
            await self.mcp_client.cleanup()
        if self.session:
            await self.session.close()
        logger.info("MCP 搜尋器資源已清理")
    
    async def search_files_by_content(self, query: SearchQuery) -> List[SearchResult]:
        """根據內容搜尋文件"""
        if not self.is_initialized:
            logger.error("MCP 客戶端未初始化")
            return []
        
        try:
            if self.mcp_client:
                # 使用統一 MCP 客戶端
                result = await self.mcp_client.call_tool('sqlite', 'search_content', {
                    'pattern': query.pattern,
                    'limit': query.max_results,
                    'file_types': query.file_extensions or []
                })
                return self._parse_mcp_search_result(result, 'content')
            else:
                # 使用 HTTP 搜尋
                return await self._http_search_content(query)
                
        except Exception as e:
            logger.error(f"內容搜尋失敗: {e}")
            return []
    
    async def search_files_by_name(self, query: SearchQuery) -> List[SearchResult]:
        """根據文件名搜尋文件"""
        if not self.is_initialized:
            logger.error("MCP 客戶端未初始化")
            return []
        
        try:
            if self.mcp_client:
                # 使用統一 MCP 客戶端
                result = await self.mcp_client.call_tool('sqlite', 'list_files', {
                    'pattern': query.pattern,
                    'limit': query.max_results
                })
                return self._parse_mcp_search_result(result, 'filename')
            else:
                # 使用 HTTP 搜尋
                return await self._http_search_filename(query)
                
        except Exception as e:
            logger.error(f"文件名搜尋失敗: {e}")
            return []
    
    async def comprehensive_search(self, query: SearchQuery) -> Dict[str, List[SearchResult]]:
        """綜合搜尋（文件名 + 內容）"""
        logger.info(f"執行綜合搜尋: {query.pattern}")
        
        results = {
            'filename_matches': [],
            'content_matches': [],
            'combined_relevance': []
        }
        
        try:
            # 並行執行文件名和內容搜尋
            filename_task = self.search_files_by_name(query)
            content_task = self.search_files_by_content(query)
            
            filename_results, content_results = await asyncio.gather(
                filename_task, content_task, return_exceptions=True
            )
            
            # 處理結果
            if not isinstance(filename_results, Exception):
                results['filename_matches'] = filename_results
            else:
                logger.error(f"文件名搜尋出錯: {filename_results}")
            
            if not isinstance(content_results, Exception):
                results['content_matches'] = content_results
            else:
                logger.error(f"內容搜尋出錯: {content_results}")
            
            # 合併和排序結果
            all_results = results['filename_matches'] + results['content_matches']
            results['combined_relevance'] = self._rank_results(all_results, query.pattern)
            
            logger.info(f"搜尋完成: 文件名 {len(results['filename_matches'])} 個, "
                       f"內容 {len(results['content_matches'])} 個")
            
        except Exception as e:
            logger.error(f"綜合搜尋失敗: {e}")
        
        return results
    
    async def search_github_actions_related(self, error_keywords: List[str]) -> List[SearchResult]:
        """搜尋 GitHub Actions 相關文件"""
        logger.info(f"搜尋 GitHub Actions 相關文件: {error_keywords}")
        
        # 定義 GitHub Actions 相關的搜尋模式
        ga_patterns = [
            r"\.github/workflows/.*\.yml",
            r"\.github/workflows/.*\.yaml", 
            "ci-enhanced",
            "workflow",
            "github",
            "actions"
        ]
        
        all_results = []
        
        for pattern in ga_patterns:
            query = SearchQuery(
                pattern=pattern,
                search_type='both',
                file_extensions=['.yml', '.yaml', '.py', '.sh'],
                max_results=10
            )
            
            try:
                results = await self.comprehensive_search(query)
                all_results.extend(results['combined_relevance'])
            except Exception as e:
                logger.error(f"搜尋模式失敗 {pattern}: {e}")
        
        # 加入錯誤關鍵字搜尋
        for keyword in error_keywords:
            query = SearchQuery(
                pattern=keyword,
                search_type='content',
                max_results=5
            )
            
            try:
                results = await self.search_files_by_content(query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"錯誤關鍵字搜尋失敗 {keyword}: {e}")
        
        # 去重和排序
        unique_results = self._deduplicate_results(all_results)
        return sorted(unique_results, key=lambda x: x.relevance_score, reverse=True)[:20]
    
    async def _http_search_content(self, query: SearchQuery) -> List[SearchResult]:
        """HTTP 方式搜尋內容"""
        try:
            payload = {
                'pattern': query.pattern,
                'limit': query.max_results,
                'include_context': query.include_context
            }
            
            async with self.session.post(
                f"{self.mcp_server_url}/search/content",
                json=payload,
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_http_search_result(data, 'content')
                else:
                    logger.error(f"HTTP 搜尋失敗: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"HTTP 內容搜尋異常: {e}")
            return []
    
    async def _http_search_filename(self, query: SearchQuery) -> List[SearchResult]:
        """HTTP 方式搜尋文件名"""
        try:
            payload = {
                'pattern': query.pattern,
                'limit': query.max_results
            }
            
            async with self.session.post(
                f"{self.mcp_server_url}/search/files",
                json=payload,
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_http_search_result(data, 'filename')
                else:
                    logger.error(f"HTTP 搜尋失敗: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"HTTP 文件名搜尋異常: {e}")
            return []
    
    def _parse_mcp_search_result(self, result: Any, match_type: str) -> List[SearchResult]:
        """解析 MCP 搜尋結果"""
        search_results = []
        
        try:
            if isinstance(result, dict) and 'files' in result:
                files_data = result['files']
            elif isinstance(result, list):
                files_data = result
            else:
                files_data = [result] if result else []
            
            for item in files_data:
                if isinstance(item, dict):
                    search_results.append(SearchResult(
                        file_path=item.get('path', ''),
                        content_snippet=item.get('content', item.get('snippet', '')),
                        relevance_score=item.get('score', 0.5),
                        match_type=match_type,
                        line_number=item.get('line_number'),
                        context_lines=item.get('context', [])
                    ))
                elif isinstance(item, str):
                    search_results.append(SearchResult(
                        file_path=item,
                        content_snippet='',
                        relevance_score=0.5,
                        match_type=match_type
                    ))
        
        except Exception as e:
            logger.error(f"解析 MCP 結果失敗: {e}")
        
        return search_results
    
    def _parse_http_search_result(self, data: Dict, match_type: str) -> List[SearchResult]:
        """解析 HTTP 搜尋結果"""
        search_results = []
        
        try:
            results = data.get('results', [])
            for item in results:
                search_results.append(SearchResult(
                    file_path=item.get('file_path', ''),
                    content_snippet=item.get('content', ''),
                    relevance_score=item.get('relevance_score', 0.5),
                    match_type=match_type,
                    line_number=item.get('line_number'),
                    context_lines=item.get('context_lines', [])
                ))
        except Exception as e:
            logger.error(f"解析 HTTP 結果失敗: {e}")
        
        return search_results
    
    def _rank_results(self, results: List[SearchResult], query_pattern: str) -> List[SearchResult]:
        """對搜尋結果進行相關性排序"""
        def calculate_relevance(result: SearchResult) -> float:
            score = result.relevance_score
            
            # 文件名匹配加分
            if query_pattern.lower() in result.file_path.lower():
                score += 0.3
            
            # GitHub Actions 相關文件加分
            if any(keyword in result.file_path.lower() for keyword in 
                   ['github', 'workflow', 'ci', 'action']):
                score += 0.2
            
            # 配置文件加分
            if any(ext in result.file_path.lower() for ext in 
                   ['.yml', '.yaml', '.json', '.toml']):
                score += 0.1
            
            return min(score, 1.0)
        
        # 重新計算相關性分數
        for result in results:
            result.relevance_score = calculate_relevance(result)
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重複結果"""
        seen_paths = set()
        unique_results = []
        
        for result in results:
            if result.file_path not in seen_paths:
                seen_paths.add(result.file_path)
                unique_results.append(result)
        
        return unique_results


class GitHubActionsFileAnalyzer:
    """GitHub Actions 文件分析器"""
    
    def __init__(self, searcher: MCPFileSearcher):
        self.searcher = searcher
    
    async def analyze_error_context(self, error_message: str, 
                                  log_content: str) -> Dict[str, Any]:
        """分析錯誤上下文，找出相關文件"""
        logger.info("開始分析錯誤上下文")
        
        # 提取錯誤關鍵字
        error_keywords = self._extract_error_keywords(error_message, log_content)
        logger.info(f"提取到錯誤關鍵字: {error_keywords}")
        
        # 搜尋相關文件
        related_files = await self.searcher.search_github_actions_related(error_keywords)
        
        # 分析文件類型
        file_analysis = self._categorize_files(related_files)
        
        return {
            'error_keywords': error_keywords,
            'related_files': [self._result_to_dict(r) for r in related_files],
            'file_categories': file_analysis,
            'suggestions': self._generate_suggestions(error_keywords, file_analysis)
        }
    
    def _extract_error_keywords(self, error_message: str, log_content: str) -> List[str]:
        """提取錯誤關鍵字"""
        keywords = set()
        
        # 常見的錯誤模式
        error_patterns = [
            r'Error: (.+)',
            r'Failed: (.+)',
            r'Exception: (.+)',
            r'No such file or directory: (.+)',
            r'Command failed: (.+)',
            r'ModuleNotFoundError: (.+)',
            r'ImportError: (.+)',
        ]
        
        import re
        
        text = f"{error_message} {log_content}"
        
        for pattern in error_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # 提取有用的關鍵字
                words = re.findall(r'\b\w+\b', match)
                keywords.update(word.lower() for word in words 
                              if len(word) > 3 and word.lower() not in 
                              ['error', 'failed', 'exception', 'command'])
        
        # 添加技術相關關鍵字
        tech_keywords = ['poetry', 'pytest', 'python', 'node', 'npm', 'docker', 
                        'workflow', 'action', 'mcp', 'sqlite']
        
        for keyword in tech_keywords:
            if keyword in text.lower():
                keywords.add(keyword)
        
        return list(keywords)[:10]  # 限制關鍵字數量
    
    def _categorize_files(self, results: List[SearchResult]) -> Dict[str, List[str]]:
        """分類文件類型"""
        categories = {
            'workflows': [],
            'source_code': [],
            'configuration': [],
            'scripts': [],
            'tests': [],
            'documentation': []
        }
        
        for result in results:
            path = result.file_path.lower()
            
            if '.github/workflows' in path:
                categories['workflows'].append(result.file_path)
            elif any(ext in path for ext in ['.py', '.js', '.ts']):
                if 'test' in path:
                    categories['tests'].append(result.file_path)
                else:
                    categories['source_code'].append(result.file_path)
            elif any(ext in path for ext in ['.yml', '.yaml', '.json', '.toml', '.ini']):
                categories['configuration'].append(result.file_path)
            elif any(ext in path for ext in ['.sh', '.bat', '.ps1']):
                categories['scripts'].append(result.file_path)
            elif any(ext in path for ext in ['.md', '.rst', '.txt']):
                categories['documentation'].append(result.file_path)
        
        return categories
    
    def _generate_suggestions(self, keywords: List[str], 
                            file_categories: Dict[str, List[str]]) -> List[str]:
        """生成修復建議"""
        suggestions = []
        
        # 基於關鍵字的建議
        if 'poetry' in keywords:
            suggestions.append("檢查 poetry.lock 文件是否需要更新")
            suggestions.append("驗證 pyproject.toml 中的依賴配置")
        
        if 'pytest' in keywords:
            suggestions.append("檢查測試文件路徑和導入語句")
            suggestions.append("確認測試環境變數設置")
        
        if 'mcp' in keywords:
            suggestions.append("驗證 MCP 服務器連接狀態")
            suggestions.append("檢查 MCP 配置文件")
        
        # 基於文件類型的建議
        if file_categories['workflows']:
            suggestions.append("檢查 GitHub Actions workflow 配置")
            suggestions.append("驗證 workflow 中的環境變數和秘密")
        
        if file_categories['configuration']:
            suggestions.append("檢查配置文件語法和路徑")
        
        return suggestions
    
    def _result_to_dict(self, result: SearchResult) -> Dict[str, Any]:
        """轉換搜尋結果為字典"""
        return {
            'file_path': result.file_path,
            'content_snippet': result.content_snippet[:200],  # 限制長度
            'relevance_score': result.relevance_score,
            'match_type': result.match_type,
            'line_number': result.line_number
        }


# =============================================================================
# 主函數和測試
# =============================================================================

async def main():
    """主函數示例"""
    searcher = MCPFileSearcher()
    
    try:
        # 初始化搜尋器
        if not await searcher.initialize():
            print("❌ MCP 搜尋器初始化失敗")
            return
        
        print("✅ MCP 搜尋器初始化成功")
        
        # 測試搜尋功能
        query = SearchQuery(
            pattern="ci-enhanced",
            search_type="both",
            max_results=5
        )
        
        print(f"\n🔍 搜尋: {query.pattern}")
        results = await searcher.comprehensive_search(query)
        
        print(f"📁 文件名匹配: {len(results['filename_matches'])} 個")
        for result in results['filename_matches'][:3]:
            print(f"  📄 {result.file_path} (分數: {result.relevance_score:.2f})")
        
        print(f"📝 內容匹配: {len(results['content_matches'])} 個")
        for result in results['content_matches'][:3]:
            print(f"  📄 {result.file_path} (分數: {result.relevance_score:.2f})")
        
        # 測試 GitHub Actions 相關搜尋
        print(f"\n🔧 GitHub Actions 相關文件搜尋:")
        ga_results = await searcher.search_github_actions_related(['error', 'failed'])
        
        for result in ga_results[:5]:
            print(f"  📄 {result.file_path} (分數: {result.relevance_score:.2f})")
        
        # 測試錯誤分析
        analyzer = GitHubActionsFileAnalyzer(searcher)
        analysis = await analyzer.analyze_error_context(
            "Poetry installation failed",
            "Error: Command failed: poetry install"
        )
        
        print(f"\n📊 錯誤分析結果:")
        print(f"  關鍵字: {analysis['error_keywords']}")
        print(f"  相關文件: {len(analysis['related_files'])} 個")
        print(f"  建議: {len(analysis['suggestions'])} 條")
        
        for suggestion in analysis['suggestions'][:3]:
            print(f"    💡 {suggestion}")
        
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        traceback.print_exc()
    
    finally:
        await searcher.cleanup()


if __name__ == "__main__":
    print("🔍 MCP 文件搜尋工具測試")
    asyncio.run(main())