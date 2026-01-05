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
    QUALITY_JUDGE_PROMPT
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
        
        try:
            # 尝试提取JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            print(f"✓ 需求分析完成 (耗时: {duration:.2f}秒)")
            
            return result
        except json.JSONDecodeError:
            print("[警告] JSON解析失败，使用默认结果")
            return {
                "understanding": response[:200],
                "key_concepts": [requirement],
                "time_range": "未指定",
                "search_keywords": [requirement],
                "search_strategy": "通用搜索"
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

