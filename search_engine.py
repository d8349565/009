"""
搜索和信息获取模块
"""
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict, Any
import re
import time
import config
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1'
        }
        # 统计信息：每次向单个关键词发起的搜索调用计数，以及每个关键词的日志
        self._total_search_calls = 0
        self._keyword_logs: List[Dict[str, Any]] = []
        # 每次 search() 调用后，保存去重后、最终筛选前的全部候选（供过程日志使用）
        self._last_all_results: List[Dict[str, Any]] = []
        # Cache fetched pages to avoid duplicate network calls across keywords.
        self._content_cache: Dict[str, str] = {}
        self._content_cache_lock = threading.Lock()
        self._content_max_length = max(0, config.CONTENT_EXTRACT_LENGTH)
        self._content_timeout = max(3, min(self.timeout, 6))
        self._retry_total = max(0, config.FETCH_RETRY_TOTAL)
        self._backoff_factor = max(0.0, config.FETCH_BACKOFF_FACTOR)
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # A separate session for page-content fetching to avoid retry-amplified stalls.
        self.fetch_session = requests.Session()
        self.fetch_session.headers.update(self.headers)
        no_retry_adapter = HTTPAdapter(max_retries=Retry(total=0))
        self.fetch_session.mount("http://", no_retry_adapter)
        self.fetch_session.mount("https://", no_retry_adapter)
        self._setup_session()

        self._thread_ctx = threading.local()
        self._fetch_failure_lock = threading.Lock()
        self._fetch_failures_by_keyword: Dict[str, Dict[str, Any]] = {}

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

        # 当主搜索引擎为SearXNG时，尝试将Tavily初始化为备用引擎
        self._tavily_fallback_client = None
        if self.engine_type == 'searxng' and TAVILY_AVAILABLE and config.TAVILY_API_KEY:
            try:
                self._tavily_fallback_client = TavilyClient(config.TAVILY_API_KEY)
                print(f"✓ Tavily已配置为SearXNG的备用搜索引擎")
            except Exception as _fe:
                print(f"  ⚠ Tavily备用引擎初始化失败: {_fe}")

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url:
            return ""
        raw = str(url).strip()
        m = re.search(r"https?://[^\s`\"']+", raw)
        candidate = m.group(0) if m else raw
        candidate = candidate.strip().strip("`'\"")
        candidate = candidate.lstrip("(").rstrip(")")
        candidate = candidate.rstrip(").,:;]}>")

        tracking_keys = {
            "spm", "from", "source", "src", "ref", "refer", "referer",
            "sid", "sessionid", "shareid", "share_token", "timestamp",
            "yclid", "s_channel", "feature", "isappinstalled", "scene",
            "clickid", "oid",
        }

        # Unwrap common search-engine redirect links and clean tracking params.
        for _ in range(3):
            try:
                parsed = urlparse(candidate)
            except Exception:
                break
            if not parsed.scheme or not parsed.netloc:
                break

            host = (parsed.hostname or "").lower()
            path = (parsed.path or "").lower()
            query = parse_qs(parsed.query, keep_blank_values=False)

            if (host in {"sogou.com", "www.sogou.com"} and path.startswith("/link")) or (
                host in {"baidu.com", "www.baidu.com"} and path == "/link"
            ):
                target = (
                    query.get("url", [None])[0]
                    or query.get("target", [None])[0]
                    or query.get("u", [None])[0]
                )
                if target:
                    candidate = unquote(target).strip()
                    continue
                return ""

            clean_query = {}
            for k, values in query.items():
                key_l = k.lower()
                if key_l.startswith("utm_") or key_l in tracking_keys:
                    continue
                clean_query[k] = values

            rebuilt = urlunparse(
                (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", urlencode(clean_query, doseq=True), "")
            )
            candidate = rebuilt.strip()
            break

        return candidate.strip()

    def _set_current_keyword(self, keyword: str):
        self._thread_ctx.current_keyword = keyword

    @staticmethod
    def _should_skip_result_url(url: str) -> bool:
        """Skip unresolved redirect/search-jump URLs."""
        if not url:
            return True
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            path = (parsed.path or "").lower()
            if host in {"sogou.com", "www.sogou.com"} and path.startswith("/link"):
                return True
            if host in {"baidu.com", "www.baidu.com"} and path == "/link":
                return True
        except Exception:
            return True
        return False

    def _get_current_keyword(self) -> str:
        return getattr(self._thread_ctx, "current_keyword", "") or ""

    def _reset_fetch_failures(self, keyword: str):
        with self._fetch_failure_lock:
            self._fetch_failures_by_keyword[keyword] = {
                "total": 0,
                "by_category": {},
            }

    def _classify_fetch_failure(self, error: Exception) -> Dict[str, str]:
        msg = f"{type(error).__name__}: {error}"
        winerr = None
        m = re.search(r"WinError\s+(\d+)", msg)
        if m:
            try:
                winerr = int(m.group(1))
            except Exception:
                winerr = None

        if isinstance(error, requests.exceptions.SSLError):
            return {"category": "SSL", "reason": msg}
        if isinstance(error, requests.exceptions.Timeout):
            return {"category": "TIMEOUT", "reason": msg}
        if isinstance(error, requests.exceptions.ConnectionError):
            if winerr == 10061:
                return {"category": "CONN_REFUSED_10061", "reason": msg}
            if winerr in (10053, 10054):
                return {"category": "CONN_ABORT_RESET_10053_10054", "reason": msg}
            return {"category": "CONNECTION_ERROR", "reason": msg}
        if isinstance(error, requests.exceptions.RequestException):
            return {"category": "REQUEST_ERROR", "reason": msg}
        return {"category": "UNKNOWN", "reason": msg}

    def _record_fetch_failure(self, keyword: str, url: str, category: str, reason: str):
        if config.FETCH_FAILURE_LOG_MODE == "silent":
            return
        url = self._normalize_url(url)
        try:
            from urllib.parse import urlparse
            hostname = (urlparse(url).hostname or "").lower()
        except Exception:
            hostname = ""

        with self._fetch_failure_lock:
            entry = self._fetch_failures_by_keyword.get(keyword)
            if not entry:
                entry = {"total": 0, "by_category": {}}
                self._fetch_failures_by_keyword[keyword] = entry
            entry["total"] += 1

            by_category = entry["by_category"]
            cat = by_category.get(category)
            if not cat:
                cat = {"count": 0, "examples": [], "domains": {}}
                by_category[category] = cat
            cat["count"] += 1
            if url and url not in cat["examples"] and len(cat["examples"]) < 3:
                cat["examples"].append(url)
            if hostname:
                cat["domains"][hostname] = cat["domains"].get(hostname, 0) + 1

    def _print_fetch_failure_summary(self, keyword: str):
        if config.FETCH_FAILURE_LOG_MODE != "summary":
            return
        with self._fetch_failure_lock:
            entry = self._fetch_failures_by_keyword.get(keyword)
        if not entry or not entry.get("total"):
            return

        name_map = {
            "SSL": "SSL/证书/握手",
            "TIMEOUT": "请求超时",
            "CONN_REFUSED_10061": "连接被拒绝(10061)",
            "CONN_ABORT_RESET_10053_10054": "连接中断/重置(10053/10054)",
            "CONNECTION_ERROR": "连接错误",
            "REQUEST_ERROR": "请求错误",
            "HTTP_403_429": "HTTP 403/429",
            "HTTP_ERROR": "HTTP 错误",
            "UNKNOWN": "未知错误",
        }

        total = int(entry.get("total", 0))
        by_category = entry.get("by_category", {}) if isinstance(entry.get("by_category"), dict) else {}
        items = sorted(by_category.items(), key=lambda kv: kv[1].get("count", 0), reverse=True)
        if not items:
            return

        print(f"⚠️ 抓取失败汇总（关键词：{keyword}）共 {total} 条")
        for cat_key, cat_val in items:
            count = int(cat_val.get("count", 0))
            label = name_map.get(cat_key, cat_key)
            examples = cat_val.get("examples", [])
            if config.LOG_LEVEL == "minimal":
                continue
            if examples:
                print(f"  - {label}: {count}（示例：{examples[0]}）")
            else:
                print(f"  - {label}: {count}")
    
    def enable_priority_sources(self, enabled: bool = True):
        """启用或禁用优先搜索源"""
        self.priority_sources_enabled = enabled
        config.PRIORITY_SOURCES["enabled"] = enabled
        if enabled:
            print(f"✓ 已启用优先搜索源（{len(config.PRIORITY_SOURCES['organizations'])}个权威机构）")
        else:
            print("✗ 未启用优先搜索源")
    
    def _setup_session(self):
        """Configure retry behavior for HTTP requests."""
        if self._retry_total <= 0:
            return
        status_forcelist = {429, 500, 502, 503, 504}
        try:
            retry = Retry(
                total=self._retry_total,
                backoff_factor=self._backoff_factor,
                status_forcelist=status_forcelist,
                allowed_methods=frozenset(["GET"])
            )
        except TypeError:
            retry = Retry(
                total=self._retry_total,
                backoff_factor=self._backoff_factor,
                status_forcelist=status_forcelist,
                method_whitelist=frozenset(["GET"])
            )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _needs_full_content(self, result: Dict[str, Any]) -> bool:
        """Decide whether a result should fetch full page content."""
        if not result.get("url"):
            return False
        content = result.get("content", "") or ""
        # Tavily already returns AI-extracted quality content;
        # only fetch full page when the excerpt is very short.
        threshold = 800 if result.get("_source_engine") == "tavily" else 500
        return len(content) < threshold

    def _fetch_for_result(self, keyword: str, url: str) -> str:
        """Fetch helper used by candidate enrichment workers."""
        self._set_current_keyword(keyword or "")
        try:
            return self.fetch_content(url)
        finally:
            self._set_current_keyword("")

    def _enrich_results_content(self, results: List[Dict[str, Any]]) -> None:
        """
        Fetch full content only for selected candidates.
        This avoids fetching pages for results that would be discarded.
        """
        candidates = [
            (idx, item)
            for idx, item in enumerate(results)
            if self._needs_full_content(item)
        ]
        if not candidates:
            return

        total_candidates = len(candidates)
        max_workers = min(8, max(1, total_candidates))
        print(f"  -> fetching content for {total_candidates} candidates with {max_workers} workers")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {}
            for idx, item in candidates:
                keyword = item.get("_search_keyword", "") or ""
                url = item.get("url", "")
                future = executor.submit(self._fetch_for_result, keyword, url)
                future_to_idx[future] = idx

            completed = 0
            upgraded = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    full_content = future.result()
                except Exception:
                    full_content = ""
                if full_content and len(full_content) > len(results[idx].get("content", "") or ""):
                    results[idx]["_snippet_len"] = len(results[idx].get("content", "") or "")
                    results[idx]["content"] = full_content
                    results[idx]["_fetched_full"] = True
                    results[idx]["_full_content_len"] = len(full_content)
                    upgraded += 1
                completed += 1
                if completed % 5 == 0 or completed == total_candidates:
                    print(f"     progress: {completed}/{total_candidates} (upgraded {upgraded})")

    def search(self, keywords: List[str]) -> List[Dict[str, str]]:
        """
        执行并行搜索（不拆解关键词，直接使用完整关键词）
        """
        print(f"\n{'='*60}")
        print(f"[步骤3] 正在并行搜索信息（{self.engine_type}引擎）...")
        print(f"{'='*60}")
        
        start_time = time.time()
        all_results = []
        # 关键词数量上限：默认5个，可通过 runtime.json 的 search.max_keywords 配置
        max_kw = getattr(config, 'MAX_SEARCH_KEYWORDS', 5)
        keywords_to_search = keywords[:max_kw]
        
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
                    future = executor.submit(self._tavily_search, keyword, False)
                else:  # 默认使用 searxng
                    future = executor.submit(self._searxng_search, keyword, False)

                future_to_keyword[future] = keyword
            
            # 收集搜索结果
            engine_failure_msgs: List[str] = []
            zero_result_keywords: List[str] = []
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
                    self._print_fetch_failure_summary(keyword)
                    if len(results) == 0:
                        zero_result_keywords.append(keyword)
                except RuntimeError as e:
                    # RuntimeError 表示所有搜索引擎都不可用（SearXNG+Tavily均失败）
                    engine_failure_msgs.append(str(e))
                    print(f"✗ 搜索引擎全部不可用: {keyword} - {e}")
                except Exception as e:
                    print(f"✗ 搜索失败: {keyword} - {str(e)}")

        # ── 自动降级：对返回 0 结果的关键词进行简化后重搜 ──
        if zero_result_keywords and len(all_results) < self.max_results // 2:
            simplified_keywords = []
            for kw in zero_result_keywords:
                words = kw.split()
                if len(words) > 2:
                    # 去掉最后一个词进行简化
                    simplified_keywords.append(" ".join(words[:-1]))
                elif len(words) == 2:
                    # 两个词分别搜索
                    simplified_keywords.extend(words)
            simplified_keywords = list(dict.fromkeys(simplified_keywords))[:3]  # 去重，最多3个
            if simplified_keywords:
                print(f"\n  ↻ {len(zero_result_keywords)} 个关键词返回 0 结果，尝试简化重搜: {simplified_keywords}")
                with ThreadPoolExecutor(max_workers=3) as retry_executor:
                    retry_futures = {}
                    for kw in simplified_keywords:
                        if self.engine_type == 'tavily':
                            f = retry_executor.submit(self._tavily_search, kw, False)
                        else:
                            f = retry_executor.submit(self._searxng_search, kw, False)
                        retry_futures[f] = kw
                    for f in as_completed(retry_futures):
                        kw = retry_futures[f]
                        try:
                            results = f.result()
                            all_results.extend(results)
                            print(f"  ✓ 简化重搜: {kw} ({len(results)}条)")
                        except Exception as e:
                            print(f"  ✗ 简化重搜失败: {kw} - {e}")

        # 如果所有关键词的搜索均因引擎故障失败，直接抛出异常终止流程
        if engine_failure_msgs and not all_results:
            combined = "；".join(engine_failure_msgs)
            raise RuntimeError(
                f"所有搜索引擎均不可用，无法继续调查。\n原因：{combined}\n"
                "请检查SearXNG服务是否正常，以及是否配置了TAVILY_API_KEY作为备用。"
            )
        
        # 记录原始结果数量
        raw_count = len(all_results)
        
        # 去重
        all_results = self._deduplicate_and_prioritize(all_results)

        # Two-stage search:
        # 1) pre-select by score/snippet
        # 2) fetch full content only for selected candidates
        target_max = max(1, self.max_results)
        # Hard-cap full-content fetch volume to avoid long stalls on slow domains.
        fetch_budget = min(
            len(all_results),
            min(20, max(8, int(target_max * 0.6)))
        )
        fetch_candidates = self._smart_select_results(all_results, fetch_budget)
        if fetch_candidates:
            print(f"  -> preselected {len(fetch_candidates)} results; fetching full content only for this set...")
            self._enrich_results_content(fetch_candidates)

            # Merge enriched content back into the full candidate pool so we still
            # can return up to MAX_SEARCH_RESULTS while only fetching a subset.
            enriched_content = {
                item.get("url", ""): item.get("content", "")
                for item in fetch_candidates
                if item.get("url")
            }
            for item in all_results:
                url = item.get("url", "")
                full_text = enriched_content.get(url, "")
                if full_text and len(full_text) > len(item.get("content", "") or ""):
                    item["content"] = full_text
        for keyword in keywords_to_search:
            self._print_fetch_failure_summary(keyword)

        # 快照：全文抓取完成后再记录，保证 content_len 反映实际内容长度
        self._last_all_results = []
        for _r in all_results:
            _entry = {k: v for k, v in _r.items() if k != 'content'}
            _entry['content_len'] = len(_r.get('content', '') or '')
            self._last_all_results.append(_entry)

        # Final selection after enrichment.
        final_results = self._smart_select_results(all_results, target_max)
        for item in final_results:
            item.pop("_search_keyword", None)
            item.pop("_source_engine", None)
        
        elapsed_time = time.time() - start_time
        
        # 显示详细统计
        if raw_count > len(all_results):
            print(f"\n共找到 {raw_count} 条搜索结果，去重后 {len(all_results)} 条 (耗时: {elapsed_time:.1f}秒)")
        else:
            print(f"\n共找到 {len(all_results)} 条搜索结果 (耗时: {elapsed_time:.1f}秒)")
        
        # 智能截取：优先取优先级高 + 内容完整的结果
        if len(all_results) > target_max:
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
            results = self._searxng_search(enhanced_keyword, True)
            
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
    
    # ------------------------------------------------------------------
    # Engine-specific scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_tavily_score(item: Dict[str, Any]) -> float:
        """
        Tavily 结果综合得分（0-1）

        分项权重：
        - Tavily 原生相关性分数（score 字段，0-1）: 60%
        - 内容质量（长度归一化）: 30%
        - 发布时间新近度: 10%
        """
        # 1. Tavily 原生相关性（0-1）
        native = float(item.get('score', 0) or 0)

        # 2. 内容质量（以 800 字为满分参考）
        content_len = len(item.get('content', '') or '')
        content_quality = min(1.0, content_len / 800)

        # 3. 新近度（发布日期越近分越高）
        recency = 0.0
        pub_date_str = (item.get('published_date', '') or '').strip()
        if pub_date_str:
            try:
                from datetime import datetime, timezone
                pub_dt = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                age_days = max(0, (datetime.now(timezone.utc) - pub_dt).days)
                recency = max(0.0, 1.0 - age_days / 365)
            except Exception:
                pass

        return native * 0.6 + content_quality * 0.3 + recency * 0.1

    def _select_tavily_results(
        self, results: List[Dict[str, Any]], max_count: int
    ) -> List[Dict[str, Any]]:
        """
        Tavily 专用筛选：依托 Tavily 原生相关性分数 + 内容质量 + 新近度排序。

        Tavily 本身已按相关性排序，此处在其基础上叠加内容质量和新近度微调，
        权威来源（priority_source）仍保持优先分配名额。
        """
        if len(results) <= max_count:
            return results

        priority = [r for r in results if r.get('priority_source')]
        normal   = [r for r in results if not r.get('priority_source')]

        normal.sort(key=self._calc_tavily_score, reverse=True)

        priority_quota = min(len(priority), max(3, max_count // 4))
        normal_quota   = max_count - priority_quota

        return (priority[:priority_quota] + normal[:normal_quota])[:max_count]

    @staticmethod
    def _select_searxng_results(
        results: List[Dict[str, Any]], max_count: int
    ) -> List[Dict[str, Any]]:
        """
        SearXNG 专用筛选：使用 SearXNG 聚合 score + 内容长度排序。
        权威来源优先，最多占 1/3 名额。
        """
        if len(results) <= max_count:
            return results

        priority = [r for r in results if r.get('priority_source')]
        normal   = [r for r in results if not r.get('priority_source')]

        def _score(item: Dict[str, Any]):
            return (float(item.get('score', 0) or 0),
                    len(item.get('content', '') or ''))

        normal.sort(key=_score, reverse=True)

        priority_quota = min(len(priority), max(5, max_count // 3))
        normal_quota   = max_count - priority_quota

        return (priority[:priority_quota] + normal[:normal_quota])[:max_count]

    def _select_mixed_results(
        self,
        tavily_items: List[Dict[str, Any]],
        searxng_items: List[Dict[str, Any]],
        max_count: int,
    ) -> List[Dict[str, Any]]:
        """
        混合引擎筛选（SearXNG 主引擎 + Tavily 备用结果并存时使用）。

        将两类结果的分数统一归一化到 0-1，叠加内容质量后合并排序。
        """
        # 归一化 SearXNG score 到 0-1
        max_searxng = max((float(r.get('score', 0) or 0) for r in searxng_items), default=1.0) or 1.0

        def unified(item: Dict[str, Any]) -> float:
            if item.get('_source_engine') == 'tavily':
                return self._calc_tavily_score(item)
            raw = float(item.get('score', 0) or 0) / max_searxng
            content_bonus = min(0.2, len(item.get('content', '') or '') / 5000)
            return raw * 0.8 + content_bonus

        all_items = tavily_items + searxng_items
        all_items.sort(key=unified, reverse=True)
        return all_items[:max_count]

    def _smart_select_results(
        self, results: List[Dict[str, Any]], max_count: int
    ) -> List[Dict[str, Any]]:
        """
        智能筛选入口：根据结果来源引擎自动选用对应策略。

        - 纯 Tavily 结果  → _select_tavily_results
          （Tavily 原生 score 0-1 + 内容质量 + 新近度）
        - 纯 SearXNG 结果 → _select_searxng_results
          （SearXNG 聚合 score + 内容长度）
        - 混合结果         → _select_mixed_results
          （两套分数归一化后统一排序）
        """
        if len(results) <= max_count:
            return results

        tavily_items  = [r for r in results if r.get('_source_engine') == 'tavily']
        searxng_items = [r for r in results if r.get('_source_engine') != 'tavily']

        if searxng_items and not tavily_items:
            return self._select_searxng_results(results, max_count)
        if tavily_items and not searxng_items:
            return self._select_tavily_results(results, max_count)
        return self._select_mixed_results(tavily_items, searxng_items, max_count)
    
    def _do_tavily_search(self, client, keyword: str, fetch_full_content: bool = True) -> List[Dict[str, str]]:
        """使用指定的Tavily客户端执行搜索（内部通用方法）。"""
        response = client.search(
            query=keyword,
            search_depth="advanced",
            max_results=self.max_results,
            include_answer=False,
            include_raw_content=False,
            include_domains=[],
            exclude_domains=[]
        )
        results = []
        seen_urls = set()
        for item in response.get('results', []):
            url = self._normalize_url(item.get('url', ''))
            if self._should_skip_result_url(url):
                continue
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            result = {
                'title': item.get('title', '无标题'),
                'url': url,
                'content': item.get('content', '') or item.get('snippet', ''),
                '_search_keyword': keyword,
                '_source_engine': 'tavily',
                # Tavily native relevance score (0-1); preserve for ranking.
                'score': float(item.get('score', 0) or 0),
                # Publication date (ISO string); used for recency scoring.
                'published_date': item.get('published_date', '') or '',
            }
            # Only fetch full page when excerpt is very short (threshold handled
            # by _needs_full_content, which uses a higher bar for Tavily).
            if fetch_full_content and self._needs_full_content(result) and result['url']:
                full_content = self.fetch_content(result['url'])
                if full_content and len(full_content) > len(result['content']):
                    result['content'] = full_content
            results.append(result)
        return results

    def _tavily_search(self, keyword: str, fetch_full_content: bool = True) -> List[Dict[str, str]]:
        """
        使用Tavily进行真实搜索（不拆解关键词）
        """
        if not self.tavily_client:
            print(f"[警告] Tavily客户端未初始化，回退到SearXNG搜索")
            return self._searxng_search(keyword, fetch_full_content)
        
        self._set_current_keyword(keyword)
        self._reset_fetch_failures(keyword)
        try:
            results = self._do_tavily_search(self.tavily_client, keyword, fetch_full_content)
            return results
        except Exception as e:
            print(f"[警告] Tavily搜索失败 ({keyword}): {e}")
            print(f"  回退到SearXNG搜索")
            return self._searxng_search(keyword, fetch_full_content)
        finally:
            self._set_current_keyword("")
    
    def _searxng_search(self, keyword: str, fetch_full_content: bool = True) -> List[Dict[str, str]]:
        """
        使用SearXNG进行真实搜索；超时或连接失败时自动切换到Tavily备用引擎。
        """
        self._set_current_keyword(keyword)
        self._reset_fetch_failures(keyword)
        try:
            # 构建SearXNG API请求
            url = f"{config.SEARXNG_BASE_URL}/search"
            headers = self.headers.copy()
            if config.SEARXNG_API_KEY:
                headers['Authorization'] = f'Bearer {config.SEARXNG_API_KEY}'

            # 同时搜索 general 和 news 两个分类，合并结果以提高召回率
            # （部分 SearXNG 实例 general 引擎被反爬封锁，但 news 引擎通常可用）
            categories_to_try = ['general', 'news']
            raw_items: list = []
            for category in categories_to_try:
                params = {
                    'q': keyword,
                    'format': 'json',
                    'categories': category,
                    'language': 'zh-CN'
                }
                try:
                    resp = self.session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=self.timeout
                    )
                    resp.raise_for_status()
                    cat_data = resp.json()
                    cat_items = cat_data.get('results', [])
                    raw_items.extend(cat_items)
                except Exception as cat_err:
                    print(f"  [SearXNG] category={category} 请求失败: {cat_err}")

            results = []
            seen_urls: set = set()

            # 解析SearXNG返回的结果，使用配置中的最大结果数
            for item in raw_items[:self.max_results * 2]:
                item_url = self._normalize_url(item.get('url', ''))
                if self._should_skip_result_url(item_url):
                    continue
                if item_url and item_url in seen_urls:
                    continue
                if item_url:
                    seen_urls.add(item_url)
                result = {
                    'title': item.get('title', '无标题'),
                    'url': item_url,
                    'content': item.get('content', '') or item.get('snippet', ''),
                    '_search_keyword': keyword,
                    '_source_engine': 'searxng',
                    'score': item.get('score', 0),  # SearXNG 聚合相关性分值
                }

                # 尝试获取完整网页内容（提高数据完整性）
                # 如果内容过短（<500字符）或内容为空，则抓取完整网页
                if fetch_full_content and (len(result['content']) < 500 or not result['content']) and result['url']:
                    full_content = self.fetch_content(result['url'])
                    if full_content and len(full_content) > len(result['content']):
                        result['content'] = full_content

                results.append(result)

            print(f"  找到 {len(results)} 条真实搜索结果")
            return results

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            err_type = type(e).__name__
            print(f"[警告] SearXNG搜索{err_type} ({keyword})")
            if getattr(self, '_tavily_fallback_client', None) is not None:
                print(f"  ⚡ 切换到Tavily备用搜索引擎...")
                try:
                    results = self._do_tavily_search(self._tavily_fallback_client, keyword, fetch_full_content)
                    print(f"  ✓ Tavily备用搜索完成，找到 {len(results)} 条结果")
                    return results
                except Exception as fe:
                    raise RuntimeError(
                        f"SearXNG {err_type}，Tavily备用引擎也失败: {fe}"
                    ) from e
            raise RuntimeError(
                f"SearXNG {err_type} 且未配置备用搜索引擎（未设置TAVILY_API_KEY）"
            ) from e

        except Exception as e:
            print(f"[警告] SearXNG搜索失败 ({keyword}): {e}")
            print(f"  返回空结果")
            return []
        finally:
            self._set_current_keyword("")
    
    def fetch_content(self, url: str) -> str:
        """
        Fetch page content for a URL.
        """
        url = self._normalize_url(url)
        if not url:
            return ""
        with self._content_cache_lock:
            cached = self._content_cache.get(url)
        if cached is not None:
            return cached

        try:
            from urllib.parse import urlparse
            hostname = (urlparse(url).hostname or "").lower()
            if (
                hostname.endswith("baike.baidu.com")
                or hostname.endswith("zhihu.com")
                or hostname.endswith("xueqiu.com")
                or hostname.endswith("m.whrisheng.com")
            ):
                return ""
        except Exception:
            pass

        content = ""
        try:
            response = self.fetch_session.get(url, headers=self.headers, timeout=self._content_timeout)
            if response.status_code in (403, 429):
                keyword = self._get_current_keyword() or "(未知关键词)"
                self._record_fetch_failure(keyword, url, "HTTP_403_429", str(response.status_code))
                if config.FETCH_FAILURE_LOG_MODE == "raw":
                    print(f"[Warning] Fetch failed ({url}): {response.status_code}")
                return ""
            response.raise_for_status()

            content_type = (response.headers.get('Content-Type') or '').lower()
            if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                from document_parser import DocumentParser
                result = DocumentParser.parse_pdf_from_bytes(response.content)
                content = result.get('content', '')
                if self._content_max_length and len(content) > self._content_max_length:
                    content = content[:self._content_max_length]
                if content:
                    with self._content_cache_lock:
                        self._content_cache[url] = content
                return content

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove scripts and styles.
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text.
            text_content = soup.get_text()

            # Normalize whitespace.
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = '\n'.join(chunk for chunk in chunks if chunk)
            if self._content_max_length and len(content) > self._content_max_length:
                content = content[:self._content_max_length]

        except requests.exceptions.SSLError as e:
            keyword = self._get_current_keyword() or "(未知关键词)"
            classified = self._classify_fetch_failure(e)
            self._record_fetch_failure(keyword, url, classified["category"], classified["reason"][:200])
            if config.FETCH_FAILURE_LOG_MODE == "raw":
                print(f"[Warning] Fetch failed ({url}): {classified['reason'][:300]}")
            return ""
        except requests.exceptions.RequestException as e:
            keyword = self._get_current_keyword() or "(未知关键词)"
            classified = self._classify_fetch_failure(e)
            self._record_fetch_failure(keyword, url, classified["category"], classified["reason"][:200])
            if config.FETCH_FAILURE_LOG_MODE == "raw":
                print(f"[Warning] Fetch failed ({url}): {classified['reason'][:300]}")
            return ""
        except Exception as e:
            keyword = self._get_current_keyword() or "(未知关键词)"
            classified = self._classify_fetch_failure(e)
            self._record_fetch_failure(keyword, url, classified["category"], classified["reason"][:200])
            if config.FETCH_FAILURE_LOG_MODE == "raw":
                print(f"[Warning] Fetch failed ({url}): {classified['reason'][:300]}")
            return ""

        if content:
            with self._content_cache_lock:
                self._content_cache[url] = content
        return content

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
