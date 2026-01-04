"""
搜索和信息获取模块
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import time
import config
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入Tavily
TAVILY_AVAILABLE = False
TAVILY_IMPORT_ERROR = None
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError as e:
    TAVILY_IMPORT_ERROR = f"ImportError: {str(e)}"
except Exception as e:
    TAVILY_IMPORT_ERROR = f"{type(e).__name__}: {str(e)}"


class SearchEngine:
    """搜索引擎封装"""
    
    def __init__(self, engine_type: str = None):
        """
        初始化搜索引擎
        
        Args:
            engine_type: 搜索引擎类型 ('searxng', 'tavily')
        """
        self.engine_type = engine_type or config.SEARCH_ENGINE_TYPE
        self.timeout = config.SEARCH_TIMEOUT
        self.max_results = config.MAX_SEARCH_RESULTS
        self.priority_sources_enabled = config.PRIORITY_SOURCES.get("enabled", False)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 统计信息：每次向单个关键词发起的搜索调用计数，以及每个关键词的日志
        self._total_search_calls = 0
        self._keyword_logs: List[Dict[str, Any]] = []
        
        # 初始化Tavily客户端（如果选择了Tavily）
        self.tavily_client = None
        if self.engine_type == 'tavily':
            if not TAVILY_AVAILABLE:
                print(f"✗ Tavily导入失败: {TAVILY_IMPORT_ERROR or '未知错误'}")
                print(f"  请运行: pip install tavily-python")
                print(f"✗ 将使用SearXNG搜索")
                self.engine_type = 'searxng'
            elif not config.TAVILY_API_KEY:
                print(f"✗ Tavily API Key未配置")
                print(f"  请在config.py或.env中设置TAVILY_API_KEY")
                print(f"✗ 将使用SearXNG搜索")
                self.engine_type = 'searxng'
            else:
                try:
                    self.tavily_client = TavilyClient(config.TAVILY_API_KEY)
                    print(f"✓ Tavily搜索引擎已初始化")
                    print(f"  API Key: {config.TAVILY_API_KEY[:15]}...")
                except Exception as e:
                    print(f"✗ Tavily客户端初始化失败: {e}")
                    print(f"✗ 将使用SearXNG搜索")
                    self.engine_type = 'searxng'
    
    def enable_priority_sources(self, enabled: bool = True):
        """启用或禁用优先搜索源"""
        self.priority_sources_enabled = enabled
        config.PRIORITY_SOURCES["enabled"] = enabled
        if enabled:
            print(f"✓ 已启用优先搜索源（{len(config.PRIORITY_SOURCES['organizations'])}个权威机构）")
        else:
            print("✗ 未启用优先搜索源")
    
    def search(self, keywords: List[str]) -> List[Dict[str, str]]:
        """
        执行并行搜索（不拆解关键词，直接使用完整关键词）
        """
        print(f"\n{'='*60}")
        print(f"[步骤3] 正在并行搜索信息（{self.engine_type}引擎）...")
        print(f"{'='*60}")
        
        start_time = time.time()
        all_results = []
        keywords_to_search = keywords[:3]  # 只使用前3个关键词
        
        # 使用线程池并行搜索（每个关键词独立搜索，不拆解）
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_keyword = {}
            
            # 为每个关键词提交搜索任务
            for keyword in keywords_to_search:
                # 记录关键词开始时间并追加到日志（end_ts/duration/results_count 后续填充）
                self._keyword_logs.append({
                    'keyword': keyword,
                    'engine': self.engine_type,
                    'start_ts': time.time(),
                    'end_ts': None,
                    'duration': None,
                    'results_count': 0
                })
                # 根据引擎类型选择搜索方法
                if self.engine_type == 'tavily':
                    future = executor.submit(self._tavily_search, keyword)
                else:  # 默认使用 searxng
                    future = executor.submit(self._searxng_search, keyword)

                future_to_keyword[future] = keyword
            
            # 收集搜索结果
            for future in as_completed(future_to_keyword):
                keyword = future_to_keyword[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                    # 更新统计
                    self._total_search_calls += 1
                    # 找到对应的关键词日志（第一个尚未填充 end_ts 的）并更新
                    for ln in self._keyword_logs:
                        if ln.get('keyword') == keyword and ln.get('end_ts') is None:
                            ln['end_ts'] = time.time()
                            ln['duration'] = ln['end_ts'] - ln['start_ts']
                            ln['results_count'] = len(results)
                            break
                    # 输出每次搜索的详细日志
                    last_ln = next((l for l in reversed(self._keyword_logs) if l.get('keyword') == keyword), None)
                    dur = last_ln.get('duration') if last_ln else None
                    print(f"✓ 完成搜索: {keyword} ({len(results)}条) - engine={self.engine_type} duration={dur:.2f}s" if dur is not None else f"✓ 完成搜索: {keyword} ({len(results)}条)")
                except Exception as e:
                    print(f"✗ 搜索失败: {keyword} - {str(e)}")
        
        # 记录原始结果数量
        raw_count = len(all_results)
        
        # 去重
        all_results = self._deduplicate_and_prioritize(all_results)
        
        elapsed_time = time.time() - start_time
        
        # 显示详细统计
        if raw_count > len(all_results):
            print(f"\n共找到 {raw_count} 条搜索结果，去重后 {len(all_results)} 条 (耗时: {elapsed_time:.1f}秒)")
        else:
            print(f"\n共找到 {len(all_results)} 条搜索结果 (耗时: {elapsed_time:.1f}秒)")
        
        # 智能截取：优先取优先级高 + 内容完整的结果
        final_results = self._smart_select_results(all_results, self.max_results)
        if len(all_results) > self.max_results:
            print(f"  → 智能筛选前 {len(final_results)} 条用于分析（配置: MAX_SEARCH_RESULTS={self.max_results}）")
        
        return final_results
    
    def _priority_search(self, keyword: str) -> List[Dict[str, str]]:
        """
        优先搜索权威来源
        """
        priority_results = []
        organizations = config.PRIORITY_SOURCES.get("organizations", [])
        
        # 为每个权威机构添加机构名到搜索关键词
        for org in organizations[:5]:  # 只取前5个权威机构避免搜索过多
            enhanced_keyword = f"{keyword} {org}"
            results = self._searxng_search(enhanced_keyword)
            
            # 标记为优先来源
            for result in results:
                result['priority_source'] = True
                result['source_organization'] = org
            
            priority_results.extend(results)
        
        return priority_results
    
    def _deduplicate_and_prioritize(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        去重并优先排列权威来源
        """
        seen_urls = set()
        unique_results = []
        priority_results = []
        normal_results = []
        
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                if result.get('priority_source'):
                    priority_results.append(result)
                else:
                    normal_results.append(result)
        
        # 优先来源排在前面
        return priority_results + normal_results
    
    def _smart_select_results(self, results: List[Dict[str, str]], max_count: int) -> List[Dict[str, str]]:
        """
        智能筛选结果：优先选择内容完整、来源权威的结果
        
        筛选策略：
        1. 优先选择权威来源（priority_source=True）
        2. 优先选择内容完整（字符数 > 300）的结果
        3. 保持多样性（不同来源混合）
        
        Args:
            results: 全部搜索结果
            max_count: 最多选择多少条
        
        Returns:
            筛选后的结果列表
        """
        if len(results) <= max_count:
            return results
        
        # 分类：权威来源 vs 普通来源
        priority_results = [r for r in results if r.get('priority_source')]
        normal_results = [r for r in results if not r.get('priority_source')]
        
        # 对普通来源按内容完整度排序
        def content_score(item):
            """计算内容完整度分数"""
            content_len = len(item.get('content', ''))
            return content_len
        
        # 对普通结果按内容长度排序（降序）
        normal_results.sort(key=content_score, reverse=True)
        
        # 分配名额：权威来源优先取，剩余名额给普通来源
        priority_quota = min(len(priority_results), max(5, max_count // 3))  # 权威来源至少占1/3但不超过30%
        normal_quota = max_count - priority_quota
        
        # 构建最终结果列表
        selected = []
        selected.extend(priority_results[:priority_quota])
        selected.extend(normal_results[:normal_quota])
        
        return selected[:max_count]
    
    def _tavily_search(self, keyword: str) -> List[Dict[str, str]]:
        """
        使用Tavily进行真实搜索（不拆解关键词）
        """
        if not self.tavily_client:
            print(f"[警告] Tavily客户端未初始化，回退到SearXNG搜索")
            return self._searxng_search(keyword)
        
        try:
            # 使用Tavily搜索，直接传入完整关键词
            response = self.tavily_client.search(
                query=keyword,
                search_depth="advanced",  # 使用高级搜索以获取更多结果
                max_results=self.max_results,  # 使用配置中的最大结果数
                include_answer=False,  # 不需要AI总结
                include_raw_content=False,  # 不需要原始HTML
                include_domains=[],
                exclude_domains=[]
            )
            
            results = []
            # 解析Tavily返回的结果
            for item in response.get('results', []):
                result = {
                    'title': item.get('title', '无标题'),
                    'url': item.get('url', ''),
                    'content': item.get('content', '') or item.get('snippet', '')
                }
                
                # 尝试获取完整网页内容（提高数据完整性）
                # 如果内容过短（<500字符）或内容为空，则抓取完整网页
                if (len(result['content']) < 500 or not result['content']) and result['url']:
                    full_content = self.fetch_content(result['url'])
                    if full_content and len(full_content) > len(result['content']):
                        result['content'] = full_content
                
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"[警告] Tavily搜索失败 ({keyword}): {e}")
            print(f"  回退到SearXNG搜索")
            return self._searxng_search(keyword)
    
    def _searxng_search(self, keyword: str) -> List[Dict[str, str]]:
        """
        使用SearXNG进行真实搜索
        """
        try:
            # 构建SearXNG API请求
            url = f"{config.SEARXNG_BASE_URL}/search"
            params = {
                'q': keyword,
                'format': 'json',
                'categories': 'general',
                'language': 'zh-CN'
            }
            
            headers = self.headers.copy()
            if config.SEARXNG_API_KEY:
                headers['Authorization'] = f'Bearer {config.SEARXNG_API_KEY}'
            
            response = requests.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 解析SearXNG返回的结果，使用配置中的最大结果数
            for item in data.get('results', [])[:self.max_results]:
                result = {
                    'title': item.get('title', '无标题'),
                    'url': item.get('url', ''),
                    'content': item.get('content', '') or item.get('snippet', '')
                }
                
                # 尝试获取完整网页内容（提高数据完整性）
                # 如果内容过短（<500字符）或内容为空，则抓取完整网页
                if (len(result['content']) < 500 or not result['content']) and result['url']:
                    full_content = self.fetch_content(result['url'])
                    if full_content and len(full_content) > len(result['content']):
                        result['content'] = full_content
                
                results.append(result)
            
            print(f"  找到 {len(results)} 条真实搜索结果")
            return results
            
        except Exception as e:
            print(f"[警告] SearXNG搜索失败 ({keyword}): {e}")
            print(f"  返回空结果")
            return []
    
    def fetch_content(self, url: str) -> str:
        """
        获取网页内容
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 获取文本
            text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text # 限制长度
        
        except Exception as e:
            print(f"[警告] 获取网页内容失败 ({url}): {e}")
            return ""
    
    def create_summary(self, results: List[Dict[str, str]]) -> str:
        """创建搜索结果概要"""
        summary = f"共找到 {len(results)} 条相关信息\n\n"
        
        for i, result in enumerate(results, 1):
            summary += f"{i}. {result['title']}\n"
            summary += f"   内容摘要: {result['content'][:150]}...\n\n"
        
        return summary

    def get_search_stats(self) -> Dict[str, Any]:
        """返回本次 SearchEngine 实例的搜索统计信息"""
        total_results = sum([ln.get('results_count', 0) for ln in self._keyword_logs])
        return {
            'total_search_calls': self._total_search_calls,
            'total_keyword_logs': len(self._keyword_logs),
            'total_results_found': total_results,
            'keyword_logs': list(self._keyword_logs)
        }
