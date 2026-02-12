"""
信息整理Agent系统 - 主程序
"""
from agents import (RequirementAnalyzer, InformationCollector, ReportWriter, 
                    QualityJudge, ComprehensiveReportWriter)
from search_engine import SearchEngine
from performance_timer import PerformanceTimer
from report_metadata import ReportMetadata, ReportIndex, extract_summary_from_markdown
from document_parser import DocumentParser
import config
import time
import json
import os
from typing import Dict, List, Any, Optional
from time_utils import beijing_now_str
from llm_providers import get_llm_manager


def print_model_configuration():
    """打印当前使用的模型配置（表格形式）"""
    try:
        from agent_config import get_active_agent_config
        
        config_data = get_active_agent_config()
        
        print("\n" + "="*80)
        print("🤖 当前使用的AI模型配置")
        print("="*80)
        
        # Agent名称映射
        agent_names = {
            "requirement_analyzer": "需求分析师",
            "information_collector": "信息收集员",
            "report_writer": "报告撰写员",
            "quality_judge": "质量评审员",
            "comprehensive_report_writer": "综合报告撰写员"
        }
        
        # 打印表头
        print(f"\n{'Agent名称':<20} {'供应商':<12} {'模型':<30} {'推理':<6} {'说明'}")
        print("-" * 80)
        
        # 打印每个Agent的配置
        for agent_key, settings in config_data.items():
            agent_name = agent_names.get(agent_key, agent_key)
            provider = settings['provider'].upper()
            model = settings.get('model') or '(自动选择)'
            reasoner = "是" if settings.get('use_reasoner') else "否"
            
            # 🔍 如果是OpenRouter，显示实际会使用的模型
            if provider == 'OPENROUTER':
                if reasoner == "是":
                    # 推理模式：使用 OPENROUTER_REASONER_MODEL
                    actual_model = os.getenv('OPENROUTER_REASONER_MODEL', model)
                else:
                    # 普通模式：使用 OPENROUTER_DEFAULT_MODEL
                    actual_model = os.getenv('OPENROUTER_DEFAULT_MODEL', model)
                model = actual_model  # 显示实际使用的模型
            
            # 优化说明：移除冗长的环境变量提示
            desc = settings.get('description', '')
            # 移除 "[供应商从.env]" 等提示，保留核心说明
            desc = desc.split('[')[0].strip() if '[' in desc else desc
            desc = desc[:20]  # 截断过长的描述
            
            print(f"{agent_name:<18} {provider:<12} {model:<30} {reasoner:<6} {desc}")
        
        print("="*80 + "\n")
        
        return config_data  # 返回配置数据供后续使用
        
    except Exception as e:
        print(f"⚠️  无法加载模型配置: {e}")
        print("使用默认配置继续...\n")
        return None


def validate_provider_configuration() -> bool:
    """校验当前 Agent 配置引用的 provider 是否可用。"""
    try:
        from agent_config import get_active_agent_config

        manager = get_llm_manager()
        available = manager.get_available_providers()
        if not available:
            print("错误: 未检测到任何可用 LLM 提供商。")
            print("请在 .env 中至少配置一个 API Key（DEEPSEEK_API_KEY / ZHIPU_API_KEY / OPENROUTER_API_KEY）。")
            return False

        active_cfg = get_active_agent_config()
        required = sorted(
            {
                str(settings.get("provider", "")).strip().lower()
                for settings in active_cfg.values()
                if isinstance(settings, dict) and str(settings.get("provider", "")).strip()
            }
        )

        missing = [provider for provider in required if not manager.has_provider(provider)]
        if missing:
            print("错误: 当前 Agent 配置中存在不可用的提供商：")
            for provider in missing:
                print(f"  - {provider}")
            print(f"当前可用提供商: {', '.join(available)}")
            print("请调整 runtime.json/.env 中的 provider 配置后重试。")
            return False

        return True
    except Exception as e:
        print(f"错误: 提供商配置校验失败: {e}")
        return False


class ResearchAgentSystem:
    """研究型Agent系统 - 支持上下文累积和迭代优化"""
    
    def __init__(self, max_iterations: int = None, search_engine_type: str = None):
        """
        初始化系统
        
        Args:
            max_iterations: 最大循环次数，默认使用配置文件中的值
            search_engine_type: 搜索引擎类型 ('tavily', 'searxng')，默认使用配置文件中的值
        """
        self.max_iterations = max_iterations or config.MAX_LOOP_COUNT
        
        # 使用配置文件中的搜索引擎类型
        if not search_engine_type:
            search_engine_type = config.SEARCH_ENGINE_TYPE
        
        # 初始化性能计时器
        self.timer = PerformanceTimer()
        
        # 初始化系统时间并注入各Agent
        self.system_datetime = beijing_now_str()

        # 初始化各个Agent（传入系统时间）
        self.requirement_analyzer = RequirementAnalyzer(system_datetime=self.system_datetime)
        self.information_collector = InformationCollector(system_datetime=self.system_datetime)
        self.report_writer = ReportWriter(system_datetime=self.system_datetime)
        self.quality_judge = QualityJudge(system_datetime=self.system_datetime)

        # 初始化搜索引擎（传入用户选择的引擎类型）
        self.search_engine = SearchEngine(engine_type=search_engine_type)
        
        # 初始化报告索引系统
        self.report_index = ReportIndex()

        # 上下文管理
        self.context = {
            'original_requirement': '',  # 原始需求
            'search_history': [],  # 搜索历史
            'collected_data': [],  # 已收集的数据
            'previous_reports': [],  # 历史报告
            'missing_aspects': [],  # 缺失的方面
            'improvement_suggestions': []  # 改进建议
        }

        print("="*60)
        print(f"信息整理Agent系统已启动（搜索引擎: {search_engine_type.upper()}）")
        print(f"系统时间: {self.system_datetime}（北京时间）")
        print(f"最大循环次数: {self.max_iterations}")
        print("="*60)
    
    def _generate_report_info(self, iterations: int) -> str:
        """
        生成报告的元信息（精简版）- 只保留核心统计数据
        """
        try:
            stats = self.search_engine.get_search_stats()
            
            # 获取总耗时
            total_duration = self.timer.get_total_duration() if hasattr(self.timer, 'get_total_duration') else 0
            
            # 计算有效数据条数
            total_data = len(self.context.get('collected_data', []))
            effective_count = sum(1 for data in self.context.get('collected_data', []) 
                                if data.get('credibility_score', 0) >= 5)
            
            # 构建精简的报告信息
            info_lines = [
                "---",
                "",
                "## 报告元数据",
                "",
                f"**研究主题**: {self.context['original_requirement']}  ",
                f"**数据来源**: {total_data} 条（有效 {effective_count} 条） | **搜索次数**: {stats.get('total_search_calls', 0)} | **总耗时**: {total_duration:.1f}秒  ",
                f"**生成时间**: {beijing_now_str()}",
                ""
            ]
            
            # 只显示可信度≥7的核心数据来源（最多5条）
            if self.context.get('collected_data'):
                high_quality_sources = [
                    data for data in self.context['collected_data']
                    if data.get('credibility_score', 0) >= 7
                ]
                
                if high_quality_sources:
                    info_lines.extend([
                        "**核心数据来源**（可信度≥7分）：",
                        ""
                    ])
                    
                    for idx, data in enumerate(high_quality_sources[:5], 1):  # 最多显示5条
                        title = data.get('title', '无标题')[:60]  # 限制标题长度
                        url = data.get('url', '')
                        credibility = data.get('credibility_score', 'N/A')
                        
                        info_lines.append(f"{idx}. [{title}]({url}) `可信度: {credibility}/10`")
                        
                        # 显示关键数据（如果存在）
                        data_found = data.get('data_found', '')
                        if data_found and data_found != '无' and data_found != '未评估':
                            # 限制关键数据长度到100字符
                            key_data_preview = data_found[:100] + ('...' if len(data_found) > 100 else '')
                            info_lines.append(f"   - 💡 关键数据: {key_data_preview}")
                    
                    info_lines.append("")
            
            return "\n".join(info_lines)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"> 报告元信息生成失败: {str(e)}"
    
    def quick_search(self, requirement: str) -> str:
        """
        快速搜索模式：一次搜索后直接生成报告，不进行多轮迭代和质量评审
        
        Args:
            requirement: 用户需求描述
            
        Returns:
            最终生成的报告
        """
        # 开始总计时
        self.timer.start_total()
        
        print(f"\n{'='*60}")
        print(f"快速搜索模式 - 处理需求: {requirement}")
        print(f"时间: {beijing_now_str()}")
        print(f"{'='*60}\n")
        
        # 保存原始需求
        self.context['original_requirement'] = requirement
        self.context['analysis_result'] = None  # 保存分析结果
        
        try:
            # 步骤1: 需求分析
            print(f"\n[步骤1] 分析需求...")
            self.timer.start("步骤1-需求分析", "分析用户需求并生成搜索关键词")
            analysis_result = self.requirement_analyzer.analyze(requirement)
            self.context['analysis_result'] = analysis_result  # 保存到上下文
            self.timer.end("步骤1-需求分析", {'keywords_count': len(analysis_result.get('search_keywords', []))})
            
            # 步骤2: 搜索策略（使用分析结果中的关键词）
            search_keywords = (
                analysis_result.get('search_keywords')
                or analysis_result.get('keywords')
                or analysis_result.get('key_concepts')
                or [requirement]
            )
            print(f"\n[步骤2] 搜索策略：全面了解主题")
            
            # 步骤3: 执行搜索
            print(f"[步骤3] 执行搜索...")
            self.timer.start("步骤3-执行搜索", f"搜索 {len(search_keywords)} 个关键词")
            search_results = self.search_engine.search(search_keywords)
            self.timer.end("步骤3-执行搜索", {'keywords_count': len(search_keywords), 'results_count': len(search_results)})
            
            # 显示搜索概要
            summary = self.search_engine.create_summary(search_results)
            print(f"✓ 找到 {len(search_results)} 条搜索结果")
            
            # 记录搜索历史
            self.context['search_history'].append({
                'iteration': 1,
                'keywords': search_keywords,
                'purpose': '快速搜索',
                'results_count': len(search_results)
            })
            
            # 步骤4: 信息评估和清理
            print(f"\n[步骤4] 评估信息可信度和相关性...")
            self.timer.start("步骤4-信息评估", f"评估 {len(search_results)} 条搜索结果")
            collection_context = f"原始需求: {requirement}\n"
            
            cleaned_result = self.information_collector.evaluate_and_clean(
                search_results, 
                collection_context
            )
            
            # 提取有效来源列表
            cleaned_data = cleaned_result.get('valid_sources', [])
            self.context['collected_data'] = cleaned_data
            self.timer.end("步骤4-信息评估", {'input_count': len(search_results), 'output_count': len(cleaned_data)})
            
            print(f"收集到有效数据: {len(cleaned_data)} 条")
            
            # 步骤5: 生成报告
            print(f"\n[步骤5] 生成报告...")
            self.timer.start("步骤5-生成报告", f"基于 {len(cleaned_data)} 条数据生成报告")
            final_report = self.report_writer.generate_report(
                requirement,
                analysis_result,
                self.context['collected_data']
            )
            self.timer.end("步骤5-生成报告", {'data_sources': len(cleaned_data)})
            
            print(f"\n{'='*60}")
            print("✓ 快速搜索完成！")
            print(f"总搜索次数: {len(self.context['search_history'])}")
            print(f"总数据量: {len(self.context['collected_data'])}")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"\n[错误] 快速搜索出现异常: {e}")
            import traceback
            traceback.print_exc()
            final_report = f"快速搜索失败: {str(e)}"
        
        # 结束总计时
        self.timer.end_total()
        
        # 打印性能报告
        self.timer.print_report(detailed=True)
        
        # 在报告末尾添加搜索信息
        report_info = self._generate_report_info(1)
        final_report_with_info = f"{final_report}\n\n{report_info}"
        
        return final_report_with_info
    
    def process_requirement(self, requirement: str) -> str:
        """
        处理用户需求的主流程（上下文累积版）
        
        Args:
            requirement: 用户需求描述
            
        Returns:
            最终生成的报告
        """
        self.timer.start_total()

        print(f"\n{'='*60}")
        print(f"开始处理需求: {requirement}")
        print(f"时间: {beijing_now_str()}")
        print(f"{'='*60}\n")
        
        # 保存原始需求
        self.context['original_requirement'] = requirement
        self.context['analysis_result'] = None  # 保存分析结果
        iteration = 0
        final_report = ""
        
        # 第一轮：需求分析（只做一次）
        print(f"\n[步骤1] 深度分析需求...")
        analysis_result = self.requirement_analyzer.analyze(requirement)
        self.context['analysis_result'] = analysis_result  # 保存到上下文
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n{'#'*60}")
            print(f"# 第 {iteration} 轮迭代")
            print(f"{'#'*60}\n")
            
            try:
                # 步骤2: 确定搜索策略
                if iteration == 1:
                    # 第一轮：基于需求分析的关键词搜索
                    search_keywords = (
                        analysis_result.get('search_keywords')
                        or analysis_result.get('keywords')
                        or analysis_result.get('key_concepts')
                        or [requirement]
                    )
                    search_purpose = "全面了解主题"
                else:
                    # 后续轮次：基于缺失方面生成搜索关键词
                    missing_aspects = self.context['missing_aspects']
                    if not missing_aspects:
                        print("[提示] 没有新的搜索目标，结束迭代")
                        break
                    
                    # 直接使用缺失方面组合原始需求作为搜索关键词
                    search_keywords = []
                    for aspect in missing_aspects[:3]:  # 最多取3个缺失方面
                        search_keywords.append(f"{requirement} {aspect}")
                    
                    search_purpose = f"补充缺失信息: {', '.join(missing_aspects[:3])}"
                
                print(f"\n[步骤2] 搜索策略: {search_purpose}")
                
                # 步骤3: 执行搜索
                print(f"[步骤3] 执行搜索...")
                search_results = self.search_engine.search(search_keywords)
                print(f"✓ 找到 {len(search_results)} 条搜索结果")
                
                # 记录搜索历史
                self.context['search_history'].append({
                    'iteration': iteration,
                    'keywords': search_keywords,
                    'purpose': search_purpose,
                    'results_count': len(search_results)
                })
                
                # 步骤4: 信息评估和清理（带上下文指导）
                print(f"\n[步骤4] 评估信息可信度和相关性...")
                
                # 构建信息收集员的上下文提示
                collection_context = f"原始需求: {self.context['original_requirement']}\n"
                if iteration > 1:
                    collection_context += f"本轮重点补充: {', '.join(missing_aspects[:3])}\n"
                    collection_context += f"已有数据量: {len(self.context['collected_data'])} 条\n"
                
                cleaned_result = self.information_collector.evaluate_and_clean(
                    search_results, 
                    collection_context
                )
                
                # 提取有效来源列表
                cleaned_data = cleaned_result.get('valid_sources', [])
                
                # 累积数据（去重）
                existing_urls = {item.get('url', '') for item in self.context['collected_data']}
                new_data_count = 0
                for item in cleaned_data:
                    if item.get('url', '') not in existing_urls:
                        self.context['collected_data'].append(item)
                        new_data_count += 1
                
                print(f"本轮新增有效数据: {new_data_count} 条，累计: {len(self.context['collected_data'])} 条")
                
                # 步骤5: 生成或更新报告
                print(f"\n[步骤5] {'生成' if iteration == 1 else '更新'}报告...")
                
                if iteration == 1:
                    # 第一轮：生成初始报告
                    final_report = self.report_writer.generate_report(
                        requirement,
                        analysis_result,
                        self.context['collected_data']
                    )
                else:
                    # 后续轮次：基于历史报告和新数据更新
                    # 只传递本轮新增的数据用于说明
                    new_data_items = [item for item in cleaned_data if item.get('url', '') not in existing_urls]
                    
                    update_prompt = f"""
原始需求: {self.context['original_requirement']}

之前的报告版本:
{self.context['previous_reports'][-1] if self.context['previous_reports'] else '无'}

本轮补充的信息重点:
{', '.join(missing_aspects[:3])}

新增数据 ({len(new_data_items)} 条):
{json.dumps(new_data_items, ensure_ascii=False, indent=2)}

全部已收集数据 ({len(self.context['collected_data'])} 条):
{json.dumps(self.context['collected_data'], ensure_ascii=False, indent=2)}

请在保留原有报告结构的基础上，重点补充和完善缺失的内容，确保数据引用包含来源链接。
"""
                    final_report = self.report_writer.generate_report(
                        update_prompt,
                        analysis_result,
                        self.context['collected_data']
                    )
                
                # 保存本轮报告到历史
                self.context['previous_reports'].append(final_report)
                
                # 步骤6: 质量判断（最后一轮跳过评审，直接输出）
                if iteration >= self.max_iterations:
                    print(f"\n[步骤6] 已达到最大迭代次数 ({self.max_iterations})，跳过质量评审 ⚡")
                    print(f"✓ 输出最终报告")
                    break
                
                print(f"\n[步骤6] 质量评审...")
                
                judge_context = {
                    'requirement': self.context['original_requirement'],
                    'report': final_report,
                    'iteration': iteration,
                    'total_data_count': len(self.context['collected_data']),
                    'previous_missing': self.context['missing_aspects'],  # 上一轮缺失的内容
                    'previous_suggestions': self.context['improvement_suggestions']  # 上一轮的建议
                }
                
                judgment = self.quality_judge.judge(
                    json.dumps(judge_context, ensure_ascii=False),
                    final_report,
                    iteration
                )
                
                # 更新上下文
                self.context['missing_aspects'] = judgment.get('missing_aspects', [])
                self.context['improvement_suggestions'] = judgment.get('improvement_suggestions', '')
                
                # 判断是否满足需求
                if judgment.get('is_satisfied', False):
                    print(f"\n{'='*60}")
                    print("✓ 报告质量满足需求，任务完成！")
                    print(f"总搜索次数: {len(self.context['search_history'])}")
                    print(f"总数据量: {len(self.context['collected_data'])}")
                    print(f"{'='*60}")
                    
                    # 首轮满足时的智能停止策略
                    if iteration == 1 and config.EARLY_STOP_ON_SATISFACTION:
                        print(f"\n💡 首轮报告质量已满足需求（配置: EARLY_STOP_ON_SATISFACTION=true）")
                        print(f"✓ 自动停止，不继续迭代")
                    
                    break
                else:
                    print(f"\n{'='*60}")
                    print("✗ 报告质量尚未满足需求")
                    print(f"仍需补充: {', '.join(self.context['missing_aspects'][:5])}")
                    print(f"改进建议: {self.context['improvement_suggestions']}")
                    print(f"{'='*60}")
                    
                    time.sleep(1)  # 短暂延迟
            
            except Exception as e:
                print(f"\n[错误] 处理过程中出现异常: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # 输出迭代统计
        print(f"\n{'='*60}")
        print("迭代统计:")
        print(f"- 总轮次: {iteration}")
        print(f"- 总搜索次数: {len(self.context['search_history'])}")
        print(f"- 累积数据量: {len(self.context['collected_data'])}")
        print(f"- 报告版本数: {len(self.context['previous_reports'])}")
        print(f"{'='*60}")
        # 打印搜索引擎的详细统计（每个关键词的调用/耗时/结果数）
        try:
            stats = self.search_engine.get_search_stats()
            print("\n搜索引擎统计:")
            print(f"- 总 API 调用次数 (每个关键词计一次): {stats.get('total_search_calls')}")
            print(f"- 记录的关键词日志数: {stats.get('total_keyword_logs')}")
            print(f"- 总结果条数 (关键词级统计): {stats.get('total_results_found')}")
            print("- 关键词明细:")
            for ln in stats.get('keyword_logs', []):
                print(f"  - {ln.get('keyword')} | engine={ln.get('engine')} | results={ln.get('results_count')} | duration={ln.get('duration')}")
        except Exception:
            pass

        self.timer.end_total()
        
        # 在报告末尾添加搜索信息
        report_info = self._generate_report_info(iteration)
        final_report_with_info = f"{final_report}\n\n{report_info}"
        
        return final_report_with_info
    
    def save_report(self, report: str, filename: str = None, auto_open: bool = True, topic: str = None, 
                    analysis_result: Dict = None, search_keywords: List[str] = None):
        """
        保存Markdown报告到reports文件夹，同时生成元数据并更新索引
        
        Args:
            report: 报告内容
            filename: 文件名（默认自动生成）
            auto_open: 是否自动打开报告（默认True）
            topic: 报告主题（用于生成有意义的文件名和元数据）
            analysis_result: 需求分析结果（包含关键词等信息）
            search_keywords: 搜索使用的关键词
        """
        import os
        import re
        
        # 创建reports文件夹（如果不存在）
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
            print(f"✓ 已创建报告文件夹: {reports_dir}/")
        
        if filename is None:
            # 如果提供了主题，使用主题生成文件名
            if topic:
                # 清理主题：去除特殊字符，保留中文、英文、数字
                clean_topic = re.sub(r'[^\u4e00-\u9fff\w\-]', '', topic)
                # 限制长度（最多30个字符）
                clean_topic = clean_topic[:30]
                timestamp = beijing_now_str('%Y%m%d_%H%M%S')
                filename = f"{clean_topic}_{timestamp}.md"
            else:
                # 如果没有主题，使用默认格式
                timestamp = beijing_now_str('%Y%m%d_%H%M%S')
                filename = f"report_{timestamp}.md"
        
        # 构建完整路径
        filepath = os.path.join(reports_dir, filename)
        
        try:
            # 保存Markdown报告
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n报告已保存到: {filepath}")
            
            # 生成并保存元数据
            self._save_report_metadata(
                filepath=filepath,
                report_content=report,
                topic=topic or "未分类",
                analysis_result=analysis_result,
                search_keywords=search_keywords
            )
            
            # 自动打开报告
            if auto_open:
                import subprocess
                print(f"正在打开报告...")
                
                # Windows系统使用默认程序打开
                if os.name == 'nt':  # Windows
                    os.startfile(filepath)
                else:  # macOS/Linux
                    subprocess.run(['xdg-open', filepath])
                    
        except Exception as e:
            print(f"\n[错误] 保存或打开报告失败: {e}")
    
    def _save_report_metadata(self, filepath: str, report_content: str, topic: str,
                             analysis_result: Dict = None, search_keywords: List[str] = None):
        """
        生成并保存报告元数据
        
        Args:
            filepath: 报告文件路径
            report_content: 报告内容
            topic: 报告主题
            analysis_result: 需求分析结果
            search_keywords: 搜索关键词
        """
        try:
            # 从报告中提取标题（第一行的# 标题）
            lines = report_content.split('\n')
            title = topic  # 默认使用主题作为标题
            for line in lines:
                if line.strip().startswith('# '):
                    title = line.strip()[2:].strip()
                    break
            
            # 提取摘要
            summary = extract_summary_from_markdown(report_content, max_length=500)
            
            # 从分析结果中提取关键词
            keywords = []
            if analysis_result:
                keywords = analysis_result.get('key_concepts', [])
                if not keywords:
                    keywords = analysis_result.get('search_keywords', [])[:5]
            
            # 使用搜索关键词
            if not search_keywords and analysis_result:
                search_keywords = analysis_result.get('search_keywords', [])
            
            # 从上下文中提取数据来源
            data_sources = []
            if hasattr(self, 'context') and self.context.get('collected_data'):
                for item in self.context['collected_data'][:10]:  # 只保存前10个
                    data_sources.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'credibility': item.get('credibility_score', 5)
                    })
            
            # 创建元数据对象
            metadata = ReportMetadata(
                title=title,
                topic=topic,
                content_summary=summary,
                keywords=keywords,
                data_sources=data_sources,
                search_keywords=search_keywords or [],
                file_path=filepath
            )
            
            # 保存元数据文件
            metadata.save_to_file(directory="reports")
            
            # 添加到索引
            self.report_index.add_report(metadata)
            
        except Exception as e:
            print(f"[警告] 元数据保存失败: {e}")
            # 不影响主流程，继续执行
    
    def comprehensive_report_mode(self, user_input: str = None, outline_file: str = None):
        """
        综合报告制作模式
        
        工作流程：
        1. 用户输入主题/纲要（或提供文件）
        2. AI分析用户意图和报告框架
        3. 从历史报告库中检索相关报告
        4. 整合多个报告，进行交叉验证
        5. 生成综合报告
        
        Args:
            user_input: 用户输入的主题或描述
            outline_file: 可选的大纲文件路径（MD/Word/PDF）
        """
        print("\n" + "="*60)
        print("🎯 综合报告制作模式")
        print("="*60 + "\n")
        
        self.timer.start_total()
        
        # 步骤1: 获取用户输入
        if not user_input and not outline_file:
            print("请选择输入方式：")
            print("1. 直接输入主题描述")
            print("2. 提供大纲文件路径（MD/Word/PDF）")
            
            choice = input("\n请选择 (1/2): ").strip()
            
            if choice == "2":
                outline_file = input("请输入文件路径: ").strip()
                if not os.path.exists(outline_file):
                    print(f"[错误] 文件不存在: {outline_file}")
                    return
                
                # 解析文件
                try:
                    self.timer.start("文件解析", "解析用户提供的大纲文件")
                    doc_data = DocumentParser.parse_file(outline_file)
                    self.timer.end("文件解析")
                    
                    print(f"\n✓ 文件解析成功！")
                    print(f"  格式: {doc_data['format'].upper()}")
                    print(f"  标题: {doc_data['title']}")
                    print(f"\n大纲预览：")
                    print(doc_data['outline'][:500])
                    
                    user_input = f"基于以下文档生成综合报告：\n\n标题: {doc_data['title']}\n\n大纲:\n{doc_data['outline']}\n\n内容:\n{doc_data['content'][:1000]}"
                    
                except Exception as e:
                    print(f"[错误] 文件解析失败: {e}")
                    return
            else:
                user_input = input("\n请输入综合报告主题: ").strip()
                if not user_input:
                    print("[错误] 主题不能为空")
                    return
        
        self.context['original_requirement'] = user_input
        
        # 步骤2: 提取关键词（用于搜索相关报告）
        self.timer.start("关键词提取", "从用户输入中提取关键词")
        
        print("\n" + "="*60)
        print("📝 步骤1: 分析用户需求")
        print("="*60)
        
        # 使用需求分析器提取关键词
        analysis_result = self.requirement_analyzer.analyze(user_input)
        keywords = analysis_result.get('keywords', [])
        topic = analysis_result.get('main_topic', '')
        
        print(f"\n提取到的关键词: {', '.join(keywords[:10])}")
        print(f"主题: {topic}")
        
        self.timer.end("关键词提取")
        
        # 步骤3: 搜索相关报告
        self.timer.start("报告检索", "从历史报告库中检索相关报告")
        
        print("\n" + "="*60)
        print("🔍 步骤2: 检索相关历史报告")
        print("="*60)
        
        # 使用ReportIndex搜索相关报告
        related_metadata = self.report_index.search(
            keywords=keywords[:5],  # 使用前5个关键词
            topic=topic,
            limit=10
        )
        
        if not related_metadata:
            print("\n[警告] 未找到相关历史报告")
            print("提示: 请先使用'单次调研模式'生成一些报告，再使用综合报告功能")
            return
        
        print(f"\n找到 {len(related_metadata)} 个相关报告：")
        for i, metadata in enumerate(related_metadata, 1):
            print(f"  {i}. {metadata.title} (主题: {metadata.topic})")
        
        # 让用户选择要整合的报告
        print("\n请选择要整合的报告：")
        print("  1. 全部使用")
        print("  2. 手动选择")
        
        choice = input("\n请选择 (1/2, 默认1): ").strip() or "1"
        
        selected_metadata = []
        if choice == "2":
            indices = input(f"请输入报告编号（用逗号分隔，如: 1,3,5）: ").strip()
            try:
                selected_indices = [int(i.strip()) - 1 for i in indices.split(',')]
                selected_metadata = [related_metadata[i] for i in selected_indices if 0 <= i < len(related_metadata)]
            except:
                print("[警告] 输入格式错误，使用全部报告")
                selected_metadata = related_metadata
        else:
            selected_metadata = related_metadata
        
        # 读取报告内容
        related_reports = []
        for metadata in selected_metadata:
            content = self.report_index.get_report_content(metadata.report_id)
            if content:
                related_reports.append({
                    'metadata': metadata,
                    'content': content
                })
        
        print(f"\n✓ 已加载 {len(related_reports)} 个报告")
        
        self.timer.end("报告检索")
        
        # 步骤4: 初始化综合报告Agent
        comprehensive_writer = ComprehensiveReportWriter(system_datetime=self.system_datetime)
        
        # 步骤5: 分析并整合报告
        self.timer.start("综合分析", "AI深度分析和整合多个报告")
        
        print("\n" + "="*60)
        print("🧠 步骤3: AI综合分析与整合")
        print("="*60)
        
        result = comprehensive_writer.analyze_and_integrate(
            user_input=user_input,
            related_reports=related_reports,
            outline_file=outline_file
        )
        
        self.timer.end("综合分析")
        
        # 步骤6: 保存综合报告
        if result and result.get('report_content'):
            report_content = result['report_content']
            
            # 添加元信息
            report_with_meta = report_content + "\n\n" + self._generate_comprehensive_report_info(
                len(selected_metadata),
                result
            )
            
            # 保存报告
            topic_for_filename = topic or "综合报告"
            self.save_report(
                report=report_with_meta,
                topic=topic_for_filename,
                analysis_result={'keywords': keywords},
                search_keywords=keywords
            )
            
            print("\n" + "="*60)
            print("✅ 综合报告制作完成！")
            print("="*60)
            
            # 显示性能统计
            print(self.timer.get_summary())
        else:
            print("\n[错误] 综合报告生成失败")
    
    def _generate_comprehensive_report_info(self, source_count: int, analysis_result: Dict) -> str:
        """生成综合报告的元信息"""
        total_duration = self.timer.get_total_duration()
        
        insights = analysis_result.get('new_insights', [])
        validation = analysis_result.get('data_validation', {})
        consistent_count = len(validation.get('consistent_data', []))
        conflicting_count = len(validation.get('conflicting_data', []))
        
        info_lines = [
            "---",
            "",
            "## 报告元信息",
            "",
            "### 综合报告信息",
            "",
            f"**报告类型**: 综合报告",
            f"**整合报告数**: {source_count}",
            f"**生成时间**: {self.system_datetime}",
            f"**总耗时**: {total_duration:.2f}秒",
            "",
            "### 数据验证",
            "",
            f"**一致数据**: {consistent_count} 个",
            f"**矛盾数据**: {conflicting_count} 个",
            "",
            "### 新发现洞察",
            ""
        ]
        
        if insights:
            for i, insight in enumerate(insights[:10], 1):
                info_lines.append(f"{i}. {insight}")
        else:
            info_lines.append("无")
        
        try:
            from agent_config import get_active_agent_config

            active_cfg = get_active_agent_config()
            provider_summary = []
            for agent_key, settings in active_cfg.items():
                if not isinstance(settings, dict):
                    continue
                provider = str(settings.get("provider", "")).strip() or "unknown"
                model = str(settings.get("model", "")).strip() or "auto"
                provider_summary.append(f"{agent_key}:{provider}/{model}")
            ai_model_summary = "; ".join(provider_summary) if provider_summary else "N/A"
        except Exception:
            ai_model_summary = "N/A"

        info_lines.extend([
            "",
            "### 系统配置",
            "",
            f"- AI模型: {ai_model_summary}",
            f"- 系统时间: {self.system_datetime}",
            ""
        ])
        
        return "\n".join(info_lines)


def main():
    """主函数"""
    # 检查 provider 配置
    if not validate_provider_configuration():
        return
    
    # 选择运行模式
    print("\n" + "="*60)
    print("🚀 信息整理Agent系统")
    print("="*60 + "\n")
    
    print("请选择运行模式：")
    print("  1. 单次调研模式 - 根据主题搜索并生成报告")
    print("  2. 综合报告制作模式 - 整合多个历史报告生成综合分析 ✨新功能")
    print("  3. 报告检索工具 - 查看和搜索历史报告")
    
    mode = input("\n请选择模式 (1/2/3, 默认1): ").strip() or "1"
    
    if mode == "2":
        # 综合报告模式
        system = ResearchAgentSystem()
        system.comprehensive_report_mode()
        return
    
    elif mode == "3":
        # 启动报告检索工具
        print("\n启动报告检索工具...")
        import report_search
        report_search.main()
        return
    
    # 单次调研模式（原有功能）
    # 示例需求
    example_requirement = "2024年中国船舶涂料销售额"
    
    print("\n" + "="*60)
    print("示例需求:", example_requirement)
    print("="*60 + "\n")
    
    # 可以让用户选择是否使用示例或输入自己的需求
    user_input = input("按回车使用示例需求，或输入你自己的需求: ").strip()
    if user_input:
        requirement = user_input
    else:
        requirement = example_requirement
    
    # 从配置文件读取所有设置
    search_mode = config.SEARCH_MODE
    max_iterations = config.MAX_LOOP_COUNT
    content_length = config.CONTENT_EXTRACT_LENGTH
    concurrent_evals = config.MAX_CONCURRENT_EVALUATIONS
    
    # 显示当前配置
    print(f"\n{'='*60}")
    print("当前配置")
    print(f"{'='*60}")
    print(f"搜索引擎: {config.SEARCH_ENGINE_TYPE.upper()}")
    print(f"搜索模式: {'快速搜索' if search_mode == 'quick' else '完整搜索'}")
    if search_mode == 'full':
        print(f"最大迭代次数: {max_iterations}")
    print(f"内容提取长度: {content_length} 字符 {'⚡' if content_length < 1000 else '📄' if content_length < 2500 else '📚'}")
    print(f"并发评估: {'串行' if concurrent_evals == 1 else f'{concurrent_evals}批并发 ⚡⚡' if concurrent_evals >= 3 else f'{concurrent_evals}批并发'}")
    
    # 性能提示
    if concurrent_evals >= 3:
        print(f"\n💡 使用并发评估（{concurrent_evals}批），大幅提速！预计耗时: 15-25秒")
    else:
        print(f"\n💡 使用串行评估，预计耗时: 30-50秒")
    
    if content_length < 1000:
        print(f"⚠️  内容提取长度较短，数据可能不完整")
    elif content_length >= 2000:
        print(f"✓ 内容提取长度适中，数据完整性良好")
    print(f"{'='*60}")
    
    # 显示模型配置
    model_config = print_model_configuration()
    
    # 创建系统实例
    system = ResearchAgentSystem(max_iterations=max_iterations)
    
    # 根据配置的模式选择处理方式
    if search_mode == 'quick':
        print("\n[模式] 使用快速搜索模式")
        report = system.quick_search(requirement)
    else:
        print("\n[模式] 使用完整搜索模式")
        report = system.process_requirement(requirement)
    
    # 从系统上下文中获取分析结果和搜索关键词
    analysis_result = system.context.get('analysis_result')
    search_keywords = None
    if system.context.get('search_history'):
        search_keywords = system.context['search_history'][0].get('keywords', [])
    
    # 根据配置决定是否显示最终报告
    if config.PRINT_FINAL_REPORT:
        print("\n" + "="*60)
        print("📄 最终报告内容")
        print("="*60 + "\n")
        print(report)
        print("\n" + "="*60 + "\n")
    else:
        print("\n✅ 报告生成完成（已跳过控制台打印，避免刷屏）")
    
    # 自动保存并打开报告
    print("\n💾 正在保存报告...")
    system.save_report(report, auto_open=True, topic=requirement, 
                      analysis_result=analysis_result, search_keywords=search_keywords)


if __name__ == "__main__":
    main()
