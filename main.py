"""
信息整理Agent系统 - 主程序
"""
from agents import (RequirementAnalyzer, InformationCollector, ReportWriter, 
                    QualityJudge)
from search_engine import SearchEngine
import config
import time
import json
from datetime import datetime


def select_search_engine():
    """让用户选择搜索引擎"""
    print("\n" + "="*60)
    print("请选择搜索引擎:")
    print("="*60)
    print("1. Tavily搜索 (推荐，需要API Key)")
    print("2. SearXNG搜索 (本地搜索引擎，无需API Key)")
    print("="*60)
    
    while True:
        choice = input("请输入选项 (1/2，直接回车默认使用SearXNG): ").strip() or "2"
        
        if choice == "1":
            return "tavily"
        elif choice == "2":
            return "searxng"
        else:
            print("无效选项，请重新输入")


class ResearchAgentSystem:
    """研究型Agent系统 - 支持上下文累积和迭代优化"""
    
    def __init__(self, max_iterations: int = None, search_engine_type: str = None):
        """
        初始化系统
        
        Args:
            max_iterations: 最大循环次数，默认使用配置文件中的值
            search_engine_type: 搜索引擎类型 ('tavily', 'searxng')
        """
        self.max_iterations = max_iterations or config.MAX_LOOP_COUNT
        
        # 如果没有指定搜索引擎类型，让用户选择
        if not search_engine_type:
            search_engine_type = select_search_engine()
        
        # 初始化系统时间并注入各Agent
        self.system_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 初始化各个Agent（传入系统时间）
        self.requirement_analyzer = RequirementAnalyzer(system_datetime=self.system_datetime)
        self.information_collector = InformationCollector(system_datetime=self.system_datetime)
        self.report_writer = ReportWriter(system_datetime=self.system_datetime)
        self.quality_judge = QualityJudge(system_datetime=self.system_datetime)

        # 初始化搜索引擎（传入用户选择的引擎类型）
        self.search_engine = SearchEngine(engine_type=search_engine_type)

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
        print(f"系统时间: {self.system_datetime}")
        print(f"最大循环次数: {self.max_iterations}")
        print("="*60)
    
    def _generate_report_info(self, iterations: int) -> str:
        """
        生成报告的元信息（搜索引擎、搜索主题等）
        """
        try:
            stats = self.search_engine.get_search_stats()
            engine_type = self.search_engine.engine_type.upper()
            
            # 构建报告信息
            info_lines = [
                "---",
                "",
                "## 报告元信息",
                "",
                f"**搜索引擎**: {engine_type}",
                f"**搜索主题**: {self.context['original_requirement']}",
                f"**迭代轮次**: {iterations}",
                f"**总搜索次数**: {stats.get('total_search_calls', 0)}",
                f"**搜索关键词数**: {stats.get('total_keyword_logs', 0)}",
                f"**收集数据条数**: {len(self.context['collected_data'])}",
                f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ]
            
            # 添加搜索关键词明细
            if stats.get('keyword_logs'):
                info_lines.append("### 搜索关键词明细")
                info_lines.append("")
                for ln in stats.get('keyword_logs', []):
                    keyword = ln.get('keyword', '')
                    results = ln.get('results_count', 0)
                    duration = ln.get('duration', 0)
                    info_lines.append(f"- **{keyword}** | 结果数: {results} | 耗时: {duration:.2f}s")
                info_lines.append("")
            
            # 添加收集到的数据来源列表
            if self.context.get('collected_data'):
                info_lines.append("### 收集到的数据来源")
                info_lines.append("")
                for idx, data in enumerate(self.context['collected_data'], 1):
                    title = data.get('title', '无标题')
                    url = data.get('url', '')
                    credibility = data.get('credibility_score', 'N/A')
                    data_found = data.get('data_found', '无')
                    
                    info_lines.append(f"**{idx}. {title}**")
                    if url:
                        info_lines.append(f"   - URL: {url}")
                    info_lines.append(f"   - 可信度: {credibility}/10")
                    info_lines.append(f"   - 关键数据: {data_found}")
                    info_lines.append("")
            
            return "\n".join(info_lines)
        except Exception as e:
            return f"> 报告元信息生成失败: {str(e)}"
    
    def quick_search(self, requirement: str) -> str:
        """
        快速搜索模式：一次搜索后直接生成报告，不进行多轮迭代和质量评审
        
        Args:
            requirement: 用户需求描述
            
        Returns:
            最终生成的报告
        """
        print(f"\n{'='*60}")
        print(f"快速搜索模式 - 处理需求: {requirement}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 保存原始需求
        self.context['original_requirement'] = requirement
        
        try:
            # 步骤1: 需求分析
            print(f"\n[步骤1] 分析需求...")
            analysis_result = self.requirement_analyzer.analyze(requirement)
            
            # 步骤2: 搜索策略（使用分析结果中的关键词）
            search_keywords = analysis_result.get('search_keywords', [requirement])
            print(f"\n[步骤2] 搜索策略：全面了解主题")
            print(f"搜索关键词: {search_keywords}")
            
            # 步骤3: 执行搜索
            print(f"\n[步骤3] 执行搜索...")
            search_results = self.search_engine.search(search_keywords)
            
            # 显示搜索概要
            summary = self.search_engine.create_summary(search_results)
            print(f"\n搜索概要:\n{summary}")
            
            # 记录搜索历史
            self.context['search_history'].append({
                'iteration': 1,
                'keywords': search_keywords,
                'purpose': '快速搜索',
                'results_count': len(search_results)
            })
            
            # 步骤4: 信息评估和清理
            print(f"\n[步骤4] 评估信息可信度和相关性...")
            collection_context = f"原始需求: {requirement}\n"
            
            cleaned_result = self.information_collector.evaluate_and_clean(
                search_results, 
                collection_context
            )
            
            # 提取有效来源列表
            cleaned_data = cleaned_result.get('valid_sources', [])
            self.context['collected_data'] = cleaned_data
            
            print(f"收集到有效数据: {len(cleaned_data)} 条")
            
            # 步骤5: 生成报告
            print(f"\n[步骤5] 生成报告...")
            final_report = self.report_writer.generate_report(
                requirement,
                analysis_result,
                self.context['collected_data']
            )
            
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
        print(f"\n{'='*60}")
        print(f"开始处理需求: {requirement}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # 保存原始需求
        self.context['original_requirement'] = requirement
        iteration = 0
        final_report = ""
        
        # 第一轮：需求分析（只做一次）
        print(f"\n[步骤1] 深度分析需求...")
        analysis_result = self.requirement_analyzer.analyze(requirement)
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n{'#'*60}")
            print(f"# 第 {iteration} 轮迭代")
            print(f"{'#'*60}\n")
            
            try:
                # 步骤2: 确定搜索策略
                if iteration == 1:
                    # 第一轮：基于需求分析的关键词搜索
                    search_keywords = analysis_result.get('search_keywords', [requirement])
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
                print(f"搜索关键词: {search_keywords}")
                
                # 步骤3: 执行搜索
                print(f"\n[步骤3] 执行搜索...")
                search_results = self.search_engine.search(search_keywords)
                
                # 显示搜索概要
                summary = self.search_engine.create_summary(search_results)
                print(f"\n搜索概要:\n{summary}")
                
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
                
                # 步骤6: 质量判断（带历史判断上下文）
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
                    break
                else:
                    print(f"\n{'='*60}")
                    print("✗ 报告质量尚未满足需求")
                    print(f"仍需补充: {', '.join(self.context['missing_aspects'][:5])}")
                    print(f"改进建议: {self.context['improvement_suggestions']}")
                    print(f"{'='*60}")
                    
                    if iteration >= self.max_iterations:
                        print(f"\n已达到最大迭代次数 ({self.max_iterations})，输出当前最佳结果。")
                        break
                    
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
        
        # 在报告末尾添加搜索信息
        report_info = self._generate_report_info(iteration)
        final_report_with_info = f"{final_report}\n\n{report_info}"
        
        return final_report_with_info
    
    def save_report(self, report: str, filename: str = None, auto_open: bool = True):
        """
        保存Markdown报告到reports文件夹并自动打开
        
        Args:
            report: 报告内容
            filename: 文件名（默认自动生成）
            auto_open: 是否自动打开报告（默认True）
        """
        import os
        
        # 创建reports文件夹（如果不存在）
        reports_dir = "reports"
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
            print(f"✓ 已创建报告文件夹: {reports_dir}/")
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{timestamp}.md"
        
        # 构建完整路径
        filepath = os.path.join(reports_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n报告已保存到: {filepath}")
            
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


def main():
    """主函数"""
    # 检查配置
    if not config.DEEPSEEK_API_KEY:
        print("错误: 请在 .env 文件中配置 DEEPSEEK_API_KEY")
        print("1. 复制 .env.example 为 .env")
        print("2. 在 .env 中填入你的 DeepSeek API 密钥")
        return
    
    # 示例需求
    example_requirement = "近五年中国船舶涂料销售额"
    
    print("\n" + "="*60)
    print("示例需求:", example_requirement)
    print("="*60 + "\n")
    
    # 可以让用户选择是否使用示例或输入自己的需求
    user_input = input("按回车使用示例需求，或输入你自己的需求: ").strip()
    if user_input:
        requirement = user_input
    else:
        requirement = example_requirement
    
    # 询问搜索模式
    print(f"\n{'='*60}")
    print("搜索模式选择")
    print(f"{'='*60}")
    print("1. 快速搜索 (一次搜索直接生成报告，速度快)")
    print("2. 完整搜索 (多轮迭代优化，质量高) ")
    print(f"{'='*60}")
    
    mode_choice = input("请选择模式 (1/2，默认1-快速): ").strip() or "1"
    quick_mode = mode_choice == "1"
    
    # 如果不是快速模式，询问最大循环次数
    if not quick_mode:
        max_iter_input = input(f"请输入最大循环次数 (默认 1): ").strip()
        max_iterations = int(max_iter_input) if max_iter_input.isdigit() else 1
    else:
        max_iterations = 1
    
    # 询问是否启用优先搜索源
    print(f"\n{'='*60}")
    print("优先搜索源配置")
    print(f"{'='*60}")
    print(f"系统可以优先搜索以下权威机构的信息：")
    for i, org in enumerate(config.PRIORITY_SOURCES["organizations"][:10], 1):
        print(f"  {i}. {org}")
    if len(config.PRIORITY_SOURCES["organizations"]) > 10:
        print(f"  ... 以及其他 {len(config.PRIORITY_SOURCES['organizations']) - 10} 个机构")
    print(f"{'='*60}")
    
    priority_choice = input("是否启用优先搜索源？(y/N): ").strip().lower()
    use_priority_sources = priority_choice in ['y', 'yes', '是']
    
    # 创建系统实例
    system = ResearchAgentSystem(max_iterations=max_iterations)
    
    # 配置搜索引擎的优先搜索源
    system.search_engine.enable_priority_sources(use_priority_sources)
    
    # 根据模式选择处理方式
    if quick_mode:
        print("\n[模式] 使用快速搜索模式")
        report = system.quick_search(requirement)
    else:
        print("\n[模式] 使用完整搜索模式")
        report = system.process_requirement(requirement)
    
    # 显示最终报告
    print("\n" + "="*60)
    print("最终报告（Markdown格式）")
    print("="*60 + "\n")
    print(report)
    print("\n" + "="*60 + "\n")
    
    # 自动保存并打开报告
    print("正在保存报告...")
    system.save_report(report, auto_open=True)


if __name__ == "__main__":
    main()
