"""
Agent基类和各种专业Agent实现
"""
from openai import OpenAI
import config
import json
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


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
        system_prompt = """你是一名专业的信息需求分析与检索专家。
你的任务是：为用户生成可直接用于搜索引擎的高质量关键词列表。

一、需求理解

准确理解用户的行业、地域、指标、时间要求

不扩展用户未提及的行业或地域范围

二、时间范围处理（强制规则）

如果用户使用模糊时间表达（如“近五年”“近三年”）：

必须拆解为连续、明确的具体年份

不得遗漏任何中间年份

示例：

近五年 → 2020–2024

近三年 → 2022–2024

关键词必须完整覆盖时间范围内的每一年

三、关键词生成规则（核心任务）

总数量：8–12 个

排序规则：按年份从近到远排列

示例：2024 → 2023 → 2022 → 2021 → 2020

四、关键词构造原则（必须遵守）
1️⃣ 年份 +1 搜索策略（优先）

查询 YYYY 年数据时，优先使用 YYYY+1 年的报告/榜单类关键词

原因：行业正式数据通常在次年发布

示例：

查询 2024 年 →

「2025 中国船舶涂料 报告」

「2025 中国船舶涂料 榜单」

2️⃣ 关键词结构要求

必须保留：

地域限定词（如：中国）

行业核心词（如：船舶涂料）

可变化：

文章类型：报告 / 榜单 / 数据 / 财报 / 排名

指标词：销售额 / 营收 / 市场规模

避免关键词过长或堆砌修饰词

3️⃣ 文章类型覆盖（整体要求）

在全部关键词中，需合理覆盖：

报告 / 白皮书类

榜单 / 排名类（优先）

新闻 / 数据披露类

公司财报 / 营收类

不要求每一年都覆盖所有类型

优先保证年份覆盖与搜索有效性

五、输出要求（强约束）

按年份分组输出（从近到远）

每个年份 2–3 个关键词

不解释规则，不输出分析过程

仅输出最终关键词列表
4. 为搜索提供指导建议

请以JSON格式返回结果：
{
    "understanding": "对需求的理解",
    "key_concepts": ["概念1", "概念2"],
    "time_range": "时间范围（必须明确具体年份）",
    "specific_years": ["2020", "2021", "2022", "2023", "2024"],
    "search_keywords": ["关键词1", "关键词2", "关键词3"],
    "search_strategy": "搜索策略建议"
}"""
        super().__init__("需求分析师", system_prompt, use_reasoner=False, system_datetime=system_datetime)
    
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
        system_prompt = """你是一名专业的信息可信度评估与数据抽取专家。
你的任务是：对单条搜索结果进行评分，并完整、结构化地提取其中的所有数据数值。

一、相关性与可信度评估

对该搜索结果与用户需求的相关性与可信度进行评分

评分范围：1–10 分

评分需综合考虑：

数据是否直接匹配需求主题

来源类型（政府 / 行业协会 / 研究机构 / 企业 / 媒体）

是否为原始数据或二次引用

数据是否注明时间、口径和对象

二、数据抽取（核心任务，强制）
1️⃣ 数值完整性（最高优先级）

必须提取文中出现的所有数值信息，包括但不限于：

金额（销售额、营收、市场规模等）

百分比（增长率、占比、渗透率等）

数量（销量、产量、企业数量等）

禁止筛选或主观判断重要性

即使数据存在冲突、重复或矛盾，也必须全部提取

2️⃣ 每条数据必须识别并标注以下属性

地域范围：全球 / 国家 / 地区 / 其他

时间属性：历史数据 / 当年数据 / 预测数据

统计口径：

总市场 / 细分市场

是否含税 / 是否含出口 / 是否为名义值

数据主体：

整体市场

单一企业

行业机构 / 协会

3️⃣ 数据来源要求

每一条数据必须保留对应的来源 URL

如果同一页面存在多组数据：

每条数据单独记录

不允许只给一个“总来源”

三、数据处理注意事项（硬规则）

全球数据 ≠ 单一国家数据

预测数据 ≠ 已发生的历史数据

不同统计口径的数据不得合并

发现口径或时间不一致时，仅标注差异，不做修正或判断

四、输出格式（JSON，强约束）

必须返回合法、可解析的 JSON

不允许输出任何非 JSON 内容

JSON 中：

字符串内的引号必须转义（使用 \\"）

不使用换行符

文本字段保持简洁，避免解释性长句

请以JSON格式返回结果：
{
    "valid_sources": [
        {
            "title": "来源标题",
            "url": "来源URL",
            "content_summary": "内容摘要",
            "credibility_score": 8,
            "key_points": ["要点1", "要点2"],
            "data_found": "发现的数据（简洁列举）"
        }
    ],
    "overall_assessment": "整体评估",
    "data_quality": "数据质量评价"
}"""
        super().__init__("信息收集员", system_prompt, use_reasoner=False, system_datetime=system_datetime)
    
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
        解析评估响应（带降级方案）
        
        Args:
            response: API响应
            original_batch: 原始批次数据（用于降级方案）
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
            return result.get('valid_sources', [])
        
        except json.JSONDecodeError:
            # 降级方案：使用简化的数据结构
            print(f"  [警告] JSON解析失败，使用降级方案")
            valid_sources = []
            for item in original_batch[:3]:  # 降级时只保留前3个
                valid_sources.append({
                    "title": item.get('title', '无标题'),
                    "url": item.get('url', ''),
                    "content_summary": item.get('content', '')[:200],
                    "credibility_score": 5,  # 默认中等可信度
                    "key_points": [],
                    "data_found": "待人工分析"
                })
            return valid_sources
        
        except Exception as e:
            print(f"  [错误] 解析异常: {str(e)}")
            return []


class ReportWriter(BaseAgent):
    """报告整理Agent"""
    
    def __init__(self, system_datetime: str = None):
        system_prompt = """你是一个专业的研究报告撰写专家。

你的任务是：
1. 整合所有收集到的有效信息
2. 组织成结构清晰的Markdown格式报告
3. 每个数据都必须标注来源，使用脚注格式 [^1]
4. 提供客观的分析和洞察

**数据使用原则**：
- 理解数据的地域、时间、口径属性后再使用
- 不同属性的数据不能直接比较
- 如有数据冲突，应说明并分析原因
- 推算的数据必须标注为"推算"并说明依据

**报告结构（Markdown格式）**：
- # 标题
- ## 执行摘要
- ## 关键发现（用脚注[^1]标注数据来源）
- ## 详细分析
  - 如有时间序列要求，包含"逐年数据分析"
  - 如需要，包含"数据验证"说明数据来源和可信度
- ## 数据来源（脚注格式）
  [^1]: [来源标题](URL)
- ## 结论和建议

**写作风格**：
- 客观、专业、简洁
- 让数据说话，不要过度解读
- 如果数据不足，坦诚说明"""
        super().__init__("报告撰写员", system_prompt, use_reasoner=True, system_datetime=system_datetime)

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
        system_prompt = """你是一个严格的质量评审专家。
你的任务是：
1. 评估报告是否充分回答了用户需求
2. 检查数据的完整性和准确性
3. 判断是否需要更多信息
4. 提供改进建议

请以JSON格式返回结果：
{
    "is_satisfied": true/false,
    "completeness_score": 8,
    "accuracy_score": 7,
    "missing_aspects": ["缺失方面1", "缺失方面2"],
    "improvement_suggestions": "改进建议",
    "decision": "满足需求" 或 "需要更多信息"
}"""
        super().__init__("质量评审员", system_prompt, use_reasoner=False, system_datetime=system_datetime)  # 启用思考模式
    
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

