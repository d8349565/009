"""
研究过程日志记录器

每次生成报告时，同步生成一份 Markdown 格式的过程记录文件，
方便用户回顾整个研究流程的逻辑与决策。
"""

import os
import re
from typing import Any, Dict, List, Optional

from time_utils import beijing_now_str


class ProcessLogger:
    """记录研究报告生成全流程，生成 Markdown 过程日志。"""

    def __init__(self, requirement: str):
        self.requirement = requirement
        self.created_at = beijing_now_str()
        self.report_filepath: str = ""

        # 各阶段数据
        self.analysis_result: Optional[Dict] = None
        self.search_engine_type: str = ""
        self.keyword_logs: List[Dict] = []      # 来自 SearchEngine.get_search_stats()
        self.all_candidates: List[Dict] = []    # 每轮去重后全部候选（含 _source_engine、score、_iteration）
        self.valid_sources: List[Dict] = []     # InformationCollector 接受的来源（已去重）
        self.filtered_out_count: int = 0        # 后置过滤移除总数
        self.cited_urls: set = set()            # 最终报告中引用的 URL
        self.quality_judgments: List[Dict] = []
        self.total_time: float = 0.0
        self.timing: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # 数据收集方法
    # ------------------------------------------------------------------

    def log_analysis(self, analysis_result: Dict) -> None:
        """记录需求分析结果（过滤掉原始 LLM 响应文本以节省空间）。"""
        self.analysis_result = {
            k: v for k, v in analysis_result.items()
            if k not in ('raw_response', 'raw_text')
        }

    def log_search_start(self, engine_type: str) -> None:
        self.search_engine_type = engine_type

    def log_search_candidates(self, candidates: List[Dict], iteration: int = 1) -> None:
        """记录某一轮搜索的全部候选结果（去重后、最终筛选前）。"""
        for c in candidates:
            fetched_full = c.get('_fetched_full', False)
            self.all_candidates.append({
                'title': (c.get('title') or '')[:80],
                'url': c.get('url', ''),
                'score': c.get('score', None),
                '_source_engine': c.get('_source_engine', ''),
                'content_len': c.get('content_len', len(c.get('content', '') or '')),
                'fetched_full': fetched_full,
                'snippet_len': c.get('_snippet_len', c.get('content_len', 0)) if not fetched_full else c.get('_snippet_len', 0),
                'full_content_len': c.get('_full_content_len', 0),
                '_iteration': iteration,
            })

    def log_keyword_stats(self, keyword_logs: List[Dict]) -> None:
        """追加关键词搜索日志（每次调用追加，不覆盖，因为多轮迭代会多次调用）。"""
        # 避免重复追加相同日志条目（比较 keyword+engine+results_count 三元组）
        existing = {
            (ln.get('keyword'), ln.get('engine'), ln.get('results_count'))
            for ln in self.keyword_logs
        }
        for ln in keyword_logs:
            key = (ln.get('keyword'), ln.get('engine'), ln.get('results_count'))
            if key not in existing:
                self.keyword_logs.append(ln)
                existing.add(key)

    def log_info_collection(self, valid_sources: List[Dict], filtered_out: int = 0) -> None:
        """记录信息员评估结果，跨迭代累积（按 URL 去重）。"""
        existing_urls = {s.get('url') for s in self.valid_sources}
        for s in valid_sources:
            url = s.get('url', '')
            if url not in existing_urls:
                self.valid_sources.append({
                    'title': (s.get('title') or '')[:80],
                    'url': url,
                    'credibility_score': s.get('credibility_score'),
                    'data_found': (s.get('data_found') or '')[:100],
                })
                existing_urls.add(url)
        self.filtered_out_count += filtered_out

    def log_report(self, report: str) -> None:
        """解析最终报告，提取被引用的 URL 集合。"""
        cited: set = set()
        # 格式: [^N]: [标题](url)
        for m in re.finditer(r'\[\^\d+\]:\s*\[.*?\]\((https?://[^\)\s]+)\)', report):
            cited.add(m.group(1).rstrip(').,;'))
        # 兜底格式: [^N]: xxx https://...
        for m in re.finditer(r'\[\^\d+\]:[^\n]*(https?://\S+)', report):
            cited.add(m.group(1).rstrip(').,;'))
        self.cited_urls = cited

    def log_quality_judgment(self, judgment: Dict, iteration: int) -> None:
        self.quality_judgments.append({
            'iteration': iteration,
            'completeness_score': judgment.get('completeness_score'),
            'accuracy_score': judgment.get('accuracy_score'),
            'is_satisfied': judgment.get('is_satisfied'),
            'missing_aspects': judgment.get('missing_aspects', []),
        })

    def log_timing(self, timer) -> None:
        """从 PerformanceTimer 提取各阶段耗时。"""
        try:
            summary = timer.get_summary()
            self.total_time = summary.get('total_time', 0)
            for name, stats in summary.get('components', {}).items():
                self.timing[name] = stats.get('total_duration', 0)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Markdown 生成
    # ------------------------------------------------------------------

    def generate_markdown(self) -> str:
        parts = [
            self._s_header(),
            self._s_user_input(),
            self._s_analysis(),
            self._s_search(),
            self._s_candidates_table(),
            self._s_info_summary(),
            self._s_quality(),
            self._s_timing(),
        ]
        return '\n\n---\n\n'.join(p for p in parts if p and p.strip())

    # ---------- 各节 ----------

    def _s_header(self) -> str:
        lines = ['# 研究过程日志', '']
        lines.append(f'**生成时间**：{self.created_at}')
        if self.report_filepath:
            lines.append(f'**报告文件**：`{os.path.basename(self.report_filepath)}`')
        if self.total_time:
            lines.append(f'**全程耗时**：{self.total_time:.1f} 秒')
        return '\n'.join(lines)

    def _s_user_input(self) -> str:
        return f'## 一、用户输入\n\n**原始需求**：{self.requirement}'

    def _s_analysis(self) -> str:
        if not self.analysis_result:
            return ''
        a = self.analysis_result
        lines = ['## 二、意图分析（需求理解）']

        understanding = a.get('understanding') or a.get('main_topic') or ''
        if understanding:
            lines.append(f'\n**AI 理解**：{str(understanding)[:400]}')

        concepts = a.get('key_concepts') or a.get('keywords') or []
        if concepts:
            lines.append(f'\n**核心概念**：{", ".join(str(c) for c in concepts[:10])}')

        time_range = a.get('time_range', '')
        if time_range:
            lines.append(f'\n**时间范围**：{time_range}')

        search_kws = a.get('search_keywords') or a.get('keywords') or []
        if search_kws:
            lines.append('\n**生成搜索词**：\n')
            for i, kw in enumerate(search_kws[:10], 1):
                lines.append(f'{i}. {kw}')

        return '\n'.join(lines)

    def _s_search(self) -> str:
        if not self.search_engine_type and not self.keyword_logs:
            return ''
        lines = ['## 三、搜索执行']
        lines.append(f'\n**搜索引擎**：{self.search_engine_type.upper() or "未知"}')
        if self.keyword_logs:
            lines.append(f'**关键词搜索记录**：\n')
            for log in self.keyword_logs:
                kw = log.get('keyword', '')
                engine = log.get('engine', self.search_engine_type)
                dur = log.get('duration')
                count = log.get('results_count', 0)
                dur_str = f'{dur:.1f}秒' if dur is not None else '—'
                lines.append(f'- `{kw}` → **{count}** 条  ｜引擎：{engine}  ｜耗时：{dur_str}')
        return '\n'.join(lines)

    def _s_candidates_table(self) -> str:
        if not self.all_candidates:
            return ''

        accepted_urls = {s.get('url') for s in self.valid_sources}
        cred_map: Dict[str, Any] = {s.get('url'): s.get('credibility_score') for s in self.valid_sources}
        has_multi_iter = len({c.get('_iteration', 1) for c in self.all_candidates}) > 1

        lines = ['## 四、搜索结果明细']
        lines.append(
            f'\n共 **{len(self.all_candidates)}** 条候选（去重后全部），'
            f'信息员接受 **{len(self.valid_sources)}** 条，'
            f'最终引用 **{len(self.cited_urls)}** 条\n'
        )

        header_cols = ['#', '标题', '来源引擎', '原始评分', '摘要字数', '抓取全文', '全文字数', '信息员评分', '是否入选', '是否引用']
        if has_multi_iter:
            header_cols.insert(1, '轮次')

        lines.append('| ' + ' | '.join(header_cols) + ' |')
        lines.append('|' + '---|' * len(header_cols))

        for i, r in enumerate(self.all_candidates, 1):
            title_raw = (r.get('title') or '').replace('|', '｜')
            url = r.get('url', '')
            title_link = f'[{title_raw[:35]}]({url})' if url else title_raw[:35]
            engine = r.get('_source_engine') or '—'
            score = r.get('score')
            score_str = f'{float(score):.3f}' if isinstance(score, (int, float)) else '—'
            fetched_full = r.get('fetched_full', False)
            # 摘要字数：抓取前的原始内容长度；全文字数：抓取后的完整内容长度
            if fetched_full:
                snippet_len = r.get('snippet_len', 0)
                full_len_str = f"{r.get('full_content_len', r.get('content_len', 0))}字"
            else:
                snippet_len = r.get('content_len', 0)
                full_len_str = '—'
            fetched_mark = '✅' if fetched_full else '❌'
            is_accepted = url in accepted_urls
            accepted_mark = '✅' if is_accepted else '❌'
            cred = cred_map.get(url, '—') if is_accepted else '—'
            cited_mark = '✅' if url in self.cited_urls else '❌'

            row = [str(i), title_link, engine, score_str, f'{snippet_len}字', fetched_mark, full_len_str, str(cred), accepted_mark, cited_mark]
            if has_multi_iter:
                row.insert(1, str(r.get('_iteration', 1)))
            lines.append('| ' + ' | '.join(row) + ' |')

        return '\n'.join(lines)

    def _s_info_summary(self) -> str:
        lines = ['## 五、信息筛选汇总']
        lines.append('\n| 统计项 | 数量 |')
        lines.append('|--------|------|')
        lines.append(f'| 搜索候选来源（去重后）| {len(self.all_candidates)} |')
        lines.append(f'| 信息员接受 | {len(self.valid_sources)} |')
        if self.filtered_out_count:
            lines.append(f'| 后置过滤移除 | {self.filtered_out_count} |')
        lines.append(f'| 报告最终引用 | {len(self.cited_urls)} |')

        if self.valid_sources:
            def _cred_int(s: Dict) -> int:
                try:
                    return int(s.get('credibility_score') or 0)
                except (TypeError, ValueError):
                    return 0

            high = sum(1 for s in self.valid_sources if _cred_int(s) >= 8)
            mid  = sum(1 for s in self.valid_sources if 5 <= _cred_int(s) < 8)
            low  = sum(1 for s in self.valid_sources if _cred_int(s) < 5)
            lines.append(
                f'\n**可信度分布**：高（≥8分）{high} 条 ｜ 中（5-7分）{mid} 条 ｜ 低（<5分）{low} 条'
            )

        return '\n'.join(lines)

    def _s_quality(self) -> str:
        if not self.quality_judgments:
            return ''
        lines = ['## 六、质量评审记录']
        for j in self.quality_judgments:
            lines.append(f'\n### 第 {j["iteration"]} 轮')
            if j.get('completeness_score') is not None:
                lines.append(f'- 完整性评分：{j["completeness_score"]}/10')
            if j.get('accuracy_score') is not None:
                lines.append(f'- 准确性评分：{j["accuracy_score"]}/10')
            satisfied = '✅ 满足需求' if j.get('is_satisfied') else '❌ 未满足'
            lines.append(f'- 评审结论：{satisfied}')
            aspects = j.get('missing_aspects', [])
            if aspects:
                lines.append(f'- 缺失方面：{", ".join(str(a) for a in aspects[:5])}')
        return '\n'.join(lines)

    def _s_timing(self) -> str:
        if not self.timing and not self.total_time:
            return ''
        lines = ['## 七、性能耗时统计', '\n| 阶段 | 耗时（秒）|', '|------|-----------|']
        for name, secs in sorted(self.timing.items(), key=lambda x: x[1], reverse=True):
            lines.append(f'| {name} | {secs:.1f} |')
        if self.total_time:
            lines.append(f'| **总计** | **{self.total_time:.1f}** |')
        return '\n'.join(lines)

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------

    def save_alongside_report(self, report_filepath: str) -> Optional[str]:
        """将过程日志保存为与报告同名的 _process_log.md 文件。"""
        self.report_filepath = report_filepath
        try:
            base = os.path.splitext(report_filepath)[0]
            log_path = f'{base}_process_log.md'
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(self.generate_markdown())
            print(f'📋 过程日志已保存：{log_path}')
            return log_path
        except Exception as e:
            print(f'[警告] 过程日志保存失败：{e}')
            return None
