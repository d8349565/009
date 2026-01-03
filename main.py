"""
信息整理Agent系统 - 主程序
"""
from agents import RequirementAnalyzer, InformationCollector, ReportWriter, QualityJudge
from search_engine import SearchEngine
import config
import time
import json
from datetime import datetime


class ResearchAgentSystem:
    """研究型Agent系统 - 支持上下文累积和迭代优化"""
    
    def __init__(self, max_iterations: int = None):
        """
        初始化系统
        
        Args:
            max_iterations: 最大循环次数，默认使用配置文件中的值
        """
        self.max_iterations = max_iterations or config.MAX_LOOP_COUNT
        
        # 初始化系统时间并注入各Agent
        self.system_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 初始化各个Agent（传入系统时间）
        self.requirement_analyzer = RequirementAnalyzer(system_datetime=self.system_datetime)
        self.information_collector = InformationCollector(system_datetime=self.system_datetime)
        self.report_writer = ReportWriter(system_datetime=self.system_datetime)
        self.quality_judge = QualityJudge(system_datetime=self.system_datetime)

        # 初始化搜索引擎
        self.search_engine = SearchEngine()

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
        print("信息整理Agent系统已启动（上下文累积模式）")
        print(f"系统时间: {self.system_datetime}")
        print(f"最大循环次数: {self.max_iterations}")
        print("="*60)
    
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
                    # 后续轮次：基于质量评审的针对性搜索
                    missing_aspects = self.context['missing_aspects']
                    if not missing_aspects:
                        print("[提示] 没有新的搜索目标，结束迭代")
                        break
                    
                    # 构建针对性搜索关键词
                    search_keywords = []
                    for aspect in missing_aspects[:3]:  # 每轮最多补充3个方面
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
        
        return final_report
    
    def save_report(self, report: str, filename: str = None, auto_open: bool = True):
        """
        保存Markdown报告到文件并自动打开
        
        Args:
            report: 报告内容
            filename: 文件名（默认自动生成）
            auto_open: 是否自动打开报告（默认True）
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{timestamp}.md"  # 改为.md扩展名
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n报告已保存到: {filename}")
            
            # 自动打开报告
            if auto_open:
                import os
                import subprocess
                print(f"正在打开报告...")
                
                # Windows系统使用默认程序打开
                if os.name == 'nt':  # Windows
                    os.startfile(filename)
                else:  # macOS/Linux
                    subprocess.run(['xdg-open', filename])
                    
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
    
    # 询问最大循环次数
    max_iter_input = input(f"请输入最大循环次数 (默认 {config.MAX_LOOP_COUNT}): ").strip()
    max_iterations = int(max_iter_input) if max_iter_input.isdigit() else config.MAX_LOOP_COUNT
    
    # 创建系统实例
    system = ResearchAgentSystem(max_iterations=max_iterations)
    
    # 处理需求
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
