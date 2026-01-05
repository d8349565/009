"""
Agent基类和各种专业Agent实现
"""
from openai import OpenAI
import config
import json
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent_prompts import (
    REQUIREMENT_ANALYZER_PROMPT,
    INFORMATION_COLLECTOR_PROMPT,
    REPORT_WRITER_PROMPT,
    QUALITY_JUDGE_PROMPT,
    COMPREHENSIVE_REPORT_WRITER_PROMPT
)


class BaseAgent:
    """Agent基类"""
    
    def __init__(self, role: str, system_prompt: str, use_reasoner: bool = False, system_datetime: str = None):
        """
        初始化Agent
        
        Args:
            role: Agent角色名称
            system_prompt: 系统提示词
            use_reasoner: 是否使用DeepSeek推理模型（思考模式）
        """
        self.role = role
        self.system_prompt = system_prompt
        self.use_reasoner = use_reasoner
        # 系统时间（由 ResearchAgentSystem 注入），用于让LLM知道当前时间
        self.system_datetime = system_datetime
        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL
        )
    
    def call_llm(self, user_message: str, temperature: float = 0.7) -> str:
        """
        调用DeepSeek API
        
        Args:
            user_message: 用户消息
            temperature: 温度参数
            
        Returns:
            AI响应内容
        """
        try:
            # 根据配置选择模型
            model = config.DEEPSEEK_REASONER if self.use_reasoner else config.DEEPSEEK_MODEL
            
            if self.use_reasoner:
                print(f"  [{self.role}] 使用思考模式进行深度分析...")
            
            # 记录API调用开始时间
            api_start_time = time.time()
            
            # 如果有系统时间，先把时间信息注入到system prompt中
            system_content = self.system_prompt
            if getattr(self, 'system_datetime', None):
                system_content = f"当前时间: {self.system_datetime}\n\n" + system_content

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature
            )
            
            # 记录API调用耗时
            api_duration = time.time() - api_start_time
            print(f"  [{self.role}] API调用耗时: {api_duration:.2f}秒")
            
            # 如果是推理模型，可能会有reasoning_content
            content = response.choices[0].message.content
            
            # 显示推理过程（如果有）
            if self.use_reasoner and hasattr(response.choices[0].message, 'reasoning_content'):
                reasoning = response.choices[0].message.reasoning_content
                if reasoning:
                    print(f"  [思考过程] {reasoning[:200]}..." if len(reasoning) > 200 else f"  [思考过程] {reasoning}")
            
            return content
        except Exception as e:
            print(f"[错误] {self.role} 调用API失败: {e}")
            return ""


class RequirementAnalyzer(BaseAgent):
    """需求理解Agent - 使用思考模式进行深度分析"""
    
    def __init__(self, system_datetime: str = None):
        super().__init__("需求分析师", REQUIREMENT_ANALYZER_PROMPT, use_reasoner=False, system_datetime=system_datetime)
    
    def analyze(self, requirement: str) -> Dict[str, Any]:
        """分析需求"""
        print(f"\n{'='*60}")
        print(f"[步骤1] 需求分析师正在分析需求...")
        print(f"{'='*60}")
        
        start_time = time.time()
        response = self.call_llm(f"用户需求：{requirement}", temperature=0.3)
        duration = time.time() - start_time
        
        print(f"  [需求分析师] API调用耗时: {duration:.2f}秒")
        
        # 首先尝试JSON解析
        json_parsed = False
        parsed_result = None
        try:
            # 尝试提取JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            parsed_result = json.loads(json_str)
            json_parsed = True
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"  [调试] JSON处理异常: {type(e).__name__}: {e}")
        
        # 如果JSON解析成功，优先使用AI返回的字段（支持多种字段名）
        if json_parsed and parsed_result:
            # 获取关键词（支持不同的字段名）
            keywords = (parsed_result.get('keywords') or 
                       parsed_result.get('key_concepts') or 
                       parsed_result.get('search_keywords') or [])
            
            # 获取主题
            main_topic = (parsed_result.get('main_topic') or 
                         parsed_result.get('topic') or 
                         parsed_result.get('understanding', ''))
            
            # 如果关键词是字符串，转换为列表
            if isinstance(keywords, str):
                keywords = [keywords]
            
            # 如果获得了有效的关键词和主题，直接返回
            if keywords and main_topic:
                print(f"✓ 需求分析完成 (耗时: {duration:.2f}秒)")
                result = parsed_result.copy()
                result['keywords'] = keywords
                result['main_topic'] = main_topic
                return result
        
        # 如果JSON解析失败或缺少关键字段，使用强化的降级逻辑
        print(f"  [调试] JSON解析失败或字段为空，使用降级逻辑")
        print(f"  [调试] 响应前300字符: {response[:300]}")
        
        import re
        
        # 策略1：尝试从AI响应中智能提取关键词
        # 查找被引号或括号括起来的内容
        quoted = re.findall(r'[\"\'\"\'《》【】]([^\"\'\"\'《》【】]{2,})[\"\'\"\'《》【】]', response)
        if quoted and len(quoted) > 0:
            keywords = quoted[:8]
        else:
            # 策略2：提取中文短语（2-6个字）
            keywords = re.findall(r'[\u4e00-\u9fff]{2,6}', requirement)
            if not keywords:
                # 策略3：按中文分隔符（，、）分割
                keywords = [w.strip() for w in requirement.replace('、', '，').split('，') if w.strip()]
            if not keywords:
                # 策略4：字符分割
                keywords = [requirement[:15], requirement[15:30]]
        
        # 过滤空值和去重，保留6个
        keywords = list(dict.fromkeys(k for k in keywords if k and len(k.strip()) > 1))[:6]
        
        # 提取主题
        topic = requirement.split('，')[0] if '，' in requirement else requirement[:50]
        if not topic:
            topic = requirement[:30]
        
        print(f"✓ 需求分析完成 (耗时: {duration:.2f}秒)")
        
        return {
            "keywords": keywords,
            "main_topic": topic,
            "understanding": response[:200],
            "search_strategy": "关键词拆分"
        }


class InformationCollector(BaseAgent):
    """信息收集和数据清理Agent"""
    
    def __init__(self, system_datetime: str = None):
        super().__init__("信息收集员", INFORMATION_COLLECTOR_PROMPT, use_reasoner=False, system_datetime=system_datetime)
    
    def evaluate_and_clean(self, search_results: List[Dict[str, str]], requirement: str, batch_size: int = 5) -> Dict[str, Any]:
        """
        评估和清理信息（批量处理优化版，支持并发）
        
        Args:
            search_results: 搜索结果列表
            requirement: 用户需求
            batch_size: 批量处理大小，默认5条一批
        """
        print(f"\n{'='*60}")
        print(f"[步骤4] 信息收集员正在评估和清理数据...")
        print(f"  待评估: {len(search_results)} 条，批量大小: {batch_size}")
        
        # 根据配置决定是否使用并发
        max_workers = config.MAX_CONCURRENT_EVALUATIONS
        use_concurrent = max_workers > 1
        
        if use_concurrent:
            print(f"  并发模式: 同时评估 {max_workers} 批 ⚡")
        else:
            print(f"  串行模式")
        print(f"{'='*60}")
        
        # 分批
        batches = [search_results[i:i+batch_size] 
                   for i in range(0, len(search_results), batch_size)]
        total_batches = len(batches)
        
        start_time = time.time()
        all_valid_sources = []
        
        if use_concurrent:
            # 并发评估
            all_valid_sources = self._evaluate_batches_concurrent(batches, requirement, max_workers)
        else:
            # 串行评估（原有逻辑）
            all_valid_sources = self._evaluate_batches_serial(batches, requirement)
        
        duration = time.time() - start_time
        
        result = {
            "valid_sources": all_valid_sources,
            "overall_assessment": f"{'并发' if use_concurrent else '串行'}评估完成，共处理 {len(search_results)} 条结果，有效来源 {len(all_valid_sources)} 个，耗时 {duration:.2f}秒",
            "data_quality": "良好" if len(all_valid_sources) > 0 else "较差"
        }
        
        # 显示结果摘要
        print(f"\n📊 评估汇总: 共找到 {len(all_valid_sources)} 个有效来源（耗时: {duration:.2f}秒）")
        if all_valid_sources:
            for i, source in enumerate(all_valid_sources[:3], 1):
                print(f"  {i}. {source.get('title', '')[:50]}... [可信度: {source.get('credibility_score', 0)}/10]")
        
        return result
    
    def _evaluate_batches_concurrent(self, batches: List[List[Dict]], requirement: str, max_workers: int) -> List[Dict]:
        """
        并发评估多个批次
        
        Args:
            batches: 批次列表
            requirement: 用户需求
            max_workers: 最大并发数
        """
        all_valid_sources = []
        total_batches = len(batches)
        
        # 使用线程池并发评估
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有批次任务
            future_to_batch = {
                executor.submit(self._evaluate_single_batch, batch, requirement, idx+1, total_batches): idx
                for idx, batch in enumerate(batches)
            }
            
            # 收集结果（按完成顺序）
            completed_count = 0
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                completed_count += 1
                
                try:
                    batch_results = future.result()
                    all_valid_sources.extend(batch_results)
                    print(f"  ✓ 批次 {batch_idx+1} 完成 ({completed_count}/{total_batches})，找到 {len(batch_results)} 个有效来源")
                except Exception as e:
                    print(f"  ✗ 批次 {batch_idx+1} 失败: {e}")
        
        return all_valid_sources
    
    def _evaluate_batches_serial(self, batches: List[List[Dict]], requirement: str) -> List[Dict]:
        """
        串行评估多个批次（原有逻辑）
        
        Args:
            batches: 批次列表
            requirement: 用户需求
        """
        all_valid_sources = []
        total_batches = len(batches)
        
        for idx, batch in enumerate(batches):
            print(f"\n⏳ 评估第 {idx+1}/{total_batches} 批 ({len(batch)} 条)...")
            batch_start = time.time()
            
            batch_results = self._evaluate_single_batch(batch, requirement, idx+1, total_batches)
            all_valid_sources.extend(batch_results)
            
            batch_duration = time.time() - batch_start
            print(f"✓ 第 {idx+1} 批完成，找到 {len(batch_results)} 个有效来源 (耗时: {batch_duration:.2f}秒)")
        
        return all_valid_sources
    
    def _evaluate_single_batch(self, batch: List[Dict], requirement: str, batch_num: int, total_batches: int) -> List[Dict]:
        """
        评估单个批次（用于并发或串行调用）
        
        Args:
            batch: 单个批次的搜索结果
            requirement: 用户需求
            batch_num: 批次编号
            total_batches: 总批次数
        """
        # 构建评估请求
        results_text = "\n\n".join([
            f"来源 {i+1}:\n标题: {r.get('title', '无标题')}\nURL: {r.get('url', '无链接')}\n内容: {r.get('content', '无内容')[:config.CONTENT_EXTRACT_LENGTH]}"
            for i, r in enumerate(batch)
        ])
        
        user_message = f"""用户需求: {requirement}

搜索结果（第{batch_num}批，共{total_batches}批）:
{results_text}

请仔细评估这些信息的有效性和可信度，提取关键数据。注意：只返回JSON格式，无需其他说明。"""
        
        response = self.call_llm(user_message, temperature=0.2)
        return self._parse_evaluation_response(response, batch)
    
    def _parse_evaluation_response(self, response: str, original_batch: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        解析评估响应（严格模式 - JSON解析失败时返回空列表）
        
        Args:
            response: API响应
            original_batch: 原始批次数据（仅用于日志）
        """
        # 尝试提取JSON
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            valid_sources = result.get('valid_sources', [])
            
            # 验证返回的数据结构
            if not isinstance(valid_sources, list):
                print(f"  [警告] valid_sources 不是列表类型，返回空结果")
                return []
            
            return valid_sources
        
        except json.JSONDecodeError as e:
            # 严格模式：JSON解析失败时不使用降级方案，直接返回空
            print(f"  [错误] JSON解析失败: {str(e)}")
            print(f"  [策略] 该批次 {len(original_batch)} 条数据被跳过，不会影响其他批次")
            # 打印部分响应用于调试
            print(f"  [调试] API响应前200字符: {response[:200]}")
            return []
        
        except Exception as e:
            print(f"  [错误] 解析异常: {str(e)}")
            print(f"  [策略] 该批次 {len(original_batch)} 条数据被跳过")
            return []


class ReportWriter(BaseAgent):
    """报告整理Agent"""
    
    def __init__(self, system_datetime: str = None):
        super().__init__("报告撰写员", REPORT_WRITER_PROMPT, use_reasoner=True, system_datetime=system_datetime)

    def generate_report(self, requirement: str, analysis: Dict, cleaned_data: List) -> str:
        """生成Markdown格式报告（优化版 - 精简输入数据）"""
        print(f"\n{'='*60}")
        print(f"[步骤5] 报告撰写员正在生成Markdown报告...")
        print(f"{'='*60}")
        
        # 根据配置决定是否精简输入数据
        if config.SIMPLIFY_REPORT_INPUT:
            # 精简模式：只发送关键信息，大幅减少prompt长度
            simplified_data = []
            for item in cleaned_data[:20]:  # 最多使用20条
                simplified_data.append({
                    "title": item.get('title', '')[:100],  # 限制标题长度
                    "url": item.get('url', ''),
                    "key_data": item.get('data_found', '未指定')[:300],  # 只要关键数据，限制长度
                    "score": item.get('credibility_score', 'N/A')
                })
            
            data_str = json.dumps(simplified_data, ensure_ascii=False, indent=2)
            print(f"  ℹ️  使用精简模式（{len(simplified_data)}条数据，约{len(data_str)}字符）")
        else:
            # 完整模式：发送所有数据
            data_str = json.dumps(cleaned_data, ensure_ascii=False, indent=2)
            print(f"  ℹ️  使用完整模式（{len(cleaned_data)}条数据，约{len(data_str)}字符）")
        
        # 简化需求分析结果
        simplified_analysis = {
            "understanding": analysis.get('understanding', '')[:200],
            "key_concepts": analysis.get('key_concepts', [])[:5],
            "time_range": analysis.get('time_range', ''),
            "search_keywords": analysis.get('search_keywords', [])[:5]
        }
        
        user_message = f"""用户需求: {requirement}

需求分析:
{json.dumps(simplified_analysis, ensure_ascii=False, indent=2)}

数据来源（{len(cleaned_data if not config.SIMPLIFY_REPORT_INPUT else simplified_data)}条）:
{data_str}

请基于以上信息生成一份简洁而全面的研究报告。要求：
1. Markdown格式
2. 包含数据分析和趋势
3. 标注数据来源
4. 保持客观准确"""
        
        prompt_length = len(user_message)
        print(f"  📊 Prompt长度: {prompt_length} 字符")
        
        report_start = time.time()
        report = self.call_llm(user_message, temperature=0.5)
        report_duration = time.time() - report_start
        
        print(f"\n✓ 报告生成完成！（耗时: {report_duration:.2f}秒）")
        return report


class QualityJudge(BaseAgent):
    """循环判断Agent - 使用思考模式进行严格评估"""
    
    def __init__(self, system_datetime: str = None):
        super().__init__("质量评审员", QUALITY_JUDGE_PROMPT, use_reasoner=False, system_datetime=system_datetime)  # 启用思考模式
    
    def judge(self, requirement: str, report: str, iteration: int) -> Dict[str, Any]:
        """判断质量"""
        print(f"\n{'='*60}")
        print(f"[步骤6] 质量评审员正在评估报告质量...")
        print(f"{'='*60}")
        
        user_message = f"""用户需求: {requirement}

当前迭代次数: {iteration}

生成的报告:
{report}

请评估这份报告是否充分满足用户需求。"""
        
        response = self.call_llm(user_message, temperature=0.2)
        
        try:
            # 尝试提取JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            print(f"\n完整性评分: {result.get('completeness_score', 0)}/10")
            print(f"准确性评分: {result.get('accuracy_score', 0)}/10")
            print(f"评审决定: {result.get('decision', '')}")
            
            if result.get('missing_aspects'):
                print(f"缺失方面: {', '.join(result.get('missing_aspects', []))}")
            
            return result
        except json.JSONDecodeError:
            print("[警告] JSON解析失败，默认判定为满足")
            return {
                "is_satisfied": True,
                "completeness_score": 7,
                "accuracy_score": 7,
                "missing_aspects": [],
                "improvement_suggestions": response[:200],
                "decision": "满足需求"
            }


class ComprehensiveReportWriter(BaseAgent):
    """综合报告撰写Agent - 负责整合多个报告生成综合分析"""
    
    def __init__(self, system_datetime: str = None):
        super().__init__(
            role="综合报告撰写员",
            system_prompt=COMPREHENSIVE_REPORT_WRITER_PROMPT,
            use_reasoner=True,  # 使用思考模式进行深度分析
            system_datetime=system_datetime
        )
    
    def analyze_and_integrate(self, 
                            user_input: str,
                            related_reports: List[Dict[str, Any]],
                            outline_file: str = None) -> Dict[str, Any]:
        """
        分析用户需求并整合多个报告
        
        Args:
            user_input: 用户输入的主题/纲要描述
            related_reports: 相关报告列表，每个包含 metadata 和 content
            outline_file: 可选的大纲文件路径（MD/Word/PDF）
            
        Returns:
            包含分析结果和综合报告的字典
        """
        print(f"\n{'='*50}")
        print(f"[{self.role}] 开始综合分析...")
        print(f"{'='*50}")
        
        # 构建用户消息
        user_message = f"""
用户需求：
{user_input}

相关历史报告数量：{len(related_reports)}

历史报告信息：
"""
        
        for i, report_data in enumerate(related_reports, 1):
            metadata = report_data.get('metadata')
            content = report_data.get('content', '')
            
            # 限制每个报告内容长度，避免token超限
            content_preview = content[:2000] if len(content) > 2000 else content
            
            user_message += f"""

### 报告 {i}
- 标题: {metadata.title}
- 主题: {metadata.topic}
- 关键词: {', '.join(metadata.keywords)}
- 标签: {', '.join(metadata.tags)}
- 摘要: {metadata.content_summary}
- 创建时间: {metadata.created_at}

内容预览：
{content_preview}
{"... (内容已截断)" if len(content) > 2000 else ""}

---
"""
        
        if outline_file:
            user_message += f"\n\n用户提供的大纲文件：{outline_file}\n"
        
        user_message += """

请完成以下任务：
1. 分析用户意图，确定报告范围和关键维度
2. 设计完整的报告大纲
3. 分析每个历史报告的相关性和可用数据
4. 进行数据交叉验证，识别一致和矛盾的数据
5. 发现跨报告的新洞察
6. 生成最终的综合报告（Markdown格式）

**必须返回完整的JSON结构（见系统提示词）**
"""
        
        response = self.call_llm(user_message, temperature=0.3)
        
        # 解析JSON响应
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            # 显示分析结果
            print("\n" + "="*50)
            print("分析结果：")
            print("="*50)
            
            analysis = result.get('analysis', {})
            print(f"\n用户意图: {analysis.get('user_intent', '未识别')}")
            print(f"报告范围: {analysis.get('report_scope', '未定义')}")
            
            if analysis.get('key_dimensions'):
                print(f"关键维度: {', '.join(analysis['key_dimensions'])}")
            
            # 显示报告大纲
            outline = analysis.get('outline', {})
            if outline:
                print(f"\n报告大纲：")
                print(f"标题: {outline.get('title', '未定义')}")
                for section in outline.get('sections', []):
                    print(f"  - {section.get('section_name', '')}")
                    for subsection in section.get('subsections', []):
                        print(f"    • {subsection}")
            
            # 显示数据验证结果
            validation = result.get('data_validation', {})
            consistent_count = len(validation.get('consistent_data', []))
            conflicting_count = len(validation.get('conflicting_data', []))
            
            print(f"\n数据验证：")
            print(f"  一致数据: {consistent_count} 个")
            print(f"  矛盾数据: {conflicting_count} 个")
            
            if conflicting_count > 0:
                print(f"\n  矛盾数据详情：")
                for conflict in validation.get('conflicting_data', [])[:3]:  # 只显示前3个
                    print(f"    • {conflict.get('data_point', '')}")
                    print(f"      来源1: {conflict.get('source1', {}).get('value', '')} ({conflict.get('source1', {}).get('from', '')})")
                    print(f"      来源2: {conflict.get('source2', {}).get('value', '')} ({conflict.get('source2', {}).get('from', '')})")
                    print(f"      建议: {conflict.get('recommendation', '')}")
            
            # 显示新洞察
            insights = result.get('new_insights', [])
            if insights:
                print(f"\n发现的新洞察：")
                for insight in insights[:5]:  # 只显示前5个
                    print(f"  • {insight}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"\n[错误] JSON解析失败: {e}")
            print(f"响应前500字符: {response[:500]}")
            
            # 返回降级结果
            return {
                "analysis": {
                    "user_intent": "解析失败",
                    "report_scope": "无法确定",
                    "key_dimensions": [],
                    "outline": {}
                },
                "related_reports_analysis": [],
                "data_validation": {
                    "consistent_data": [],
                    "conflicting_data": []
                },
                "new_insights": [],
                "report_content": "# 错误\n\n综合报告生成失败，请检查日志。\n\n原始响应：\n" + response[:1000]
            }

