"""
Agent基类和各种专业Agent实现
"""
from openai import OpenAI
import config
import json
from typing import List, Dict, Any


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
        system_prompt = """你是一个专业的需求分析专家。
你的任务是：
1. 深入理解用户的信息需求
2. 识别关键概念和时间范围
3. 生成精准的搜索关键词（3-5个）
4. 为搜索提供指导建议

请以JSON格式返回结果：
{
    "understanding": "对需求的理解",
    "key_concepts": ["概念1", "概念2"],
    "time_range": "时间范围",
    "search_keywords": ["关键词1", "关键词2", "关键词3"],
    "search_strategy": "搜索策略建议"
}"""
        super().__init__("需求分析师", system_prompt, use_reasoner=False, system_datetime=system_datetime)  # 启用思考模式
    
    def analyze(self, requirement: str) -> Dict[str, Any]:
        """分析需求"""
        print(f"\n{'='*60}")
        print(f"[步骤1] 需求分析师正在分析需求...")
        print(f"{'='*60}")
        
        response = self.call_llm(f"用户需求：{requirement}", temperature=0.3)
        
        try:
            # 尝试提取JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            print(f"\n需求理解: {result.get('understanding', '')}")
            print(f"关键概念: {', '.join(result.get('key_concepts', []))}")
            print(f"时间范围: {result.get('time_range', '')}")
            print(f"搜索关键词: {', '.join(result.get('search_keywords', []))}")
            print(f"搜索策略: {result.get('search_strategy', '')}")
            
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
    """信息收集和数据清理Agent - 使用思考模式进行深度评估"""
    
    def __init__(self, system_datetime: str = None):
        system_prompt = """你是一个专业的信息评估和数据清理专家。
你的任务是：
1. 评估搜索结果的相关性和可信度
2. 识别有效信息并过滤无效内容
3. 对每条信息进行可信度评分（1-10分）
4. 提取关键数据和要点
5. **重要**: 保留每个数据的来源URL，用于报告中标注

请以JSON格式返回结果：
{
    "valid_sources": [
        {
            "title": "来源标题",
            "url": "来源URL",
            "content_summary": "内容摘要",
            "credibility_score": 8,
            "key_points": ["要点1", "要点2"],
            "data_found": "发现的具体数据"
        }
    ],
    "overall_assessment": "整体评估",
    "data_quality": "数据质量评价"
}"""
        super().__init__("信息收集员", system_prompt, use_reasoner=False, system_datetime=system_datetime)  # 启用思考模式
    
    def evaluate_and_clean(self, search_results: List[Dict[str, str]], requirement: str) -> Dict[str, Any]:
        """评估和清理信息"""
        print(f"\n{'='*60}")
        print(f"[步骤4] 信息收集员正在评估和清理数据...")
        print(f"{'='*60}")
        
        # 构建评估请求（包含URL）
        results_text = "\n\n".join([
            f"来源 {i+1}:\n标题: {r.get('title', '无标题')}\nURL: {r.get('url', '无链接')}\n内容: {r.get('content', '无内容')[:500]}"
            for i, r in enumerate(search_results)
        ])
        
        user_message = f"""用户需求: {requirement}

搜索结果:
{results_text}

请评估这些信息的有效性和可信度，提取关键数据。"""
        
        response = self.call_llm(user_message, temperature=0.3)
        
        try:
            # 尝试提取JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            print(f"\n找到 {len(result.get('valid_sources', []))} 个有效来源")
            for i, source in enumerate(result.get('valid_sources', [])[:3], 1):
                print(f"\n来源 {i}:")
                print(f"  标题: {source.get('title', '')}")
                print(f"  URL: {source.get('url', '无链接')}")
                print(f"  可信度: {source.get('credibility_score', 0)}/10")
                print(f"  关键数据: {source.get('data_found', '无')}")
            
            print(f"\n整体评估: {result.get('overall_assessment', '')}")
            
            return result
        except json.JSONDecodeError:
            print("[警告] JSON解析失败，使用默认结果")
            return {
                "valid_sources": [],
                "overall_assessment": response[:300],
                "data_quality": "无法准确评估"
            }


class ReportWriter(BaseAgent):
    """报告整理Agent"""
    
    def __init__(self, system_datetime: str = None):
        system_prompt = """你是一个专业的研究报告撰写专家。
你的任务是：
1. 整合所有收集到的有效信息
2. 组织成结构清晰的Markdown格式报告
3. 突出关键数据和发现
4. **重要**: 每个数据和引用都必须标注来源，使用Markdown超链接格式 [来源标题](URL)
5. 提供分析和洞察

报告应包含（Markdown格式）：
- # 标题（使用一级标题）
- ## 执行摘要（使用二级标题）
- ## 关键发现（含具体数据，每个数据用[^1]标注，并在文末列出完整来源链接）
- ## 详细分析（使用三级标题分节）
- ## 数据来源（列表格式，包含标题和完整URL超链接）
- ## 结论和建议

**格式要求**：
- 必须使用Markdown语法
- 数据引用格式：根据[来源名称](URL)的数据...
- 或使用脚注：数据内容[^1]，然后在文末：[^1]: [来源标题](URL)
- 使用表格呈现数值数据（如果适用）
- 使用列表呈现要点"""
        super().__init__("报告撰写员", system_prompt, use_reasoner=True, system_datetime=system_datetime)

    def generate_report(self, requirement: str, analysis: Dict, cleaned_data: Dict) -> str:
        """生成Markdown格式报告"""
        print(f"\n{'='*60}")
        print(f"[步骤5] 报告撰写员正在生成Markdown报告...")
        print(f"{'='*60}")
        
        user_message = f"""用户需求: {requirement}

需求分析结果:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

清理后的数据:
{json.dumps(cleaned_data, ensure_ascii=False, indent=2)}

请基于以上信息生成一份完整的研究报告。"""
        
        report = self.call_llm(user_message, temperature=0.5)
        
        print("\n报告生成完成！")
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
        super().__init__("质量评审员", system_prompt, use_reasoner=True, system_datetime=system_datetime)  # 启用思考模式
    
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
