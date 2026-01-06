#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多供应商功能演示
展示如何为不同Agent配置不同的LLM供应商
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from agents import RequirementAnalyzer, InformationCollector, ReportWriter, QualityJudge
from llm_providers import get_llm_manager

def demo_different_providers():
    """演示：不同Agent使用不同的提供商"""
    print("\n" + "="*70)
    print("演示：为不同Agent配置不同的LLM供应商")
    print("="*70 + "\n")
    
    # 场景描述
    print("📋 场景说明：")
    print("  我们想要优化成本和性能：")
    print("  - 需求分析（简单任务）→ 使用GLM-4-Flash（快速便宜）")
    print("  - 信息收集（批量任务）→ 使用DeepSeek（高性价比）")
    print("  - 报告撰写（核心任务）→ 使用DeepSeek Reasoner（高质量）")
    print("  - 质量评审（评估任务）→ 使用GLM（快速反馈）")
    print()
    
    # 创建不同配置的Agent
    print("🔧 创建Agent实例...\n")
    
    # 1. 需求分析师 - 使用GLM（如果可用）
    print("1️⃣  创建需求分析师")
    analyzer = RequirementAnalyzer(provider="glm")  # 会自动回退到deepseek如果GLM不可用
    print(f"   ✓ 使用提供商: {analyzer.provider_name.upper()}")
    print(f"   ✓ 优势: {'中文理解强，响应快' if analyzer.provider_name == 'glm' else '高性价比'}")
    print()
    
    # 2. 信息收集员 - 使用DeepSeek
    print("2️⃣  创建信息收集员")
    collector = InformationCollector(provider="deepseek")
    print(f"   ✓ 使用提供商: {collector.provider_name.upper()}")
    print(f"   ✓ 优势: 批量处理成本低")
    print()
    
    # 3. 报告撰写员 - 使用DeepSeek Reasoner
    print("3️⃣  创建报告撰写员")
    writer = ReportWriter(provider="deepseek")
    print(f"   ✓ 使用提供商: {writer.provider_name.upper()}")
    print(f"   ✓ 使用推理模式: {writer.use_reasoner}")
    print(f"   ✓ 优势: 深度推理能力强，报告质量高")
    print()
    
    # 4. 质量评审员 - 使用GLM
    print("4️⃣  创建质量评审员")
    judge = QualityJudge(provider="glm")
    print(f"   ✓ 使用提供商: {judge.provider_name.upper()}")
    print(f"   ✓ 优势: {'快速评估，中文准确' if judge.provider_name == 'glm' else '稳定可靠'}")
    print()

def demo_cost_comparison():
    """演示：成本对比分析"""
    print("\n" + "="*70)
    print("成本对比分析")
    print("="*70 + "\n")
    
    scenarios = {
        "全部使用DeepSeek Chat": {
            "需求分析": ("deepseek-chat", 0.1),
            "信息收集": ("deepseek-chat", 2.0),  # 批量处理
            "报告撰写": ("deepseek-chat", 0.5),
            "质量评审": ("deepseek-chat", 0.3),
        },
        "全部使用DeepSeek Reasoner": {
            "需求分析": ("deepseek-reasoner", 1.0),
            "信息收集": ("deepseek-reasoner", 15.0),
            "报告撰写": ("deepseek-reasoner", 4.0),
            "质量评审": ("deepseek-reasoner", 2.0),
        },
        "混合配置（推荐）": {
            "需求分析": ("glm-4-flash", 0.05),
            "信息收集": ("deepseek-chat", 2.0),
            "报告撰写": ("deepseek-reasoner", 4.0),
            "质量评审": ("glm-4-flash", 0.15),
        },
        "高端配置": {
            "需求分析": ("glm-4.7", 1.5),
            "信息收集": ("deepseek-chat", 2.0),
            "报告撰写": ("xiaomi/mimo-v2-flash:free", 20.0),
            "质量评审": ("glm-4.7", 1.0),
        }
    }
    
    for scenario_name, config in scenarios.items():
        total_cost = sum(cost for _, cost in config.values())
        print(f"📊 {scenario_name}")
        for task, (model, cost) in config.items():
            print(f"   {task:12s}: {model:20s} ¥{cost:.2f}")
        print(f"   {'总成本':12s}: {'':<20s} ¥{total_cost:.2f}")
        print()

def demo_usage_guide():
    """演示：配置使用指南"""
    print("\n" + "="*70)
    print("配置使用指南")
    print("="*70 + "\n")
    
    print("📝 在 .env 文件中配置：\n")
    
    print("# 方案1: 经济型配置（推荐新手）")
    print("REQUIREMENT_ANALYZER_PROVIDER=deepseek")
    print("INFORMATION_COLLECTOR_PROVIDER=deepseek")
    print("REPORT_WRITER_PROVIDER=deepseek")
    print("QUALITY_JUDGE_PROVIDER=deepseek")
    print()
    
    print("# 方案2: 混合配置（推荐）")
    print("REQUIREMENT_ANALYZER_PROVIDER=glm        # 中文理解")
    print("INFORMATION_COLLECTOR_PROVIDER=deepseek  # 批量处理")
    print("REPORT_WRITER_PROVIDER=deepseek          # 推理能力")
    print("QUALITY_JUDGE_PROVIDER=glm               # 快速评估")
    print()
    
    print("# 方案3: 高端配置")
    print("REQUIREMENT_ANALYZER_PROVIDER=glm")
    print("INFORMATION_COLLECTOR_PROVIDER=deepseek")
    print("REPORT_WRITER_PROVIDER=openrouter")
    print("QUALITY_JUDGE_PROVIDER=glm")
    print("OPENROUTER_DEFAULT_MODEL=xiaomi/mimo-v2-flash:free")
    print()

def demo_available_models():
    """演示：显示所有可用的模型"""
    print("\n" + "="*70)
    print("当前系统可用的LLM供应商")
    print("="*70 + "\n")
    
    manager = get_llm_manager()
    available = manager.get_available_providers()
    
    if not available:
        print("❌ 未检测到任何可用的供应商")
        print("   请在 .env 文件中配置至少一个API密钥：")
        print("   - DEEPSEEK_API_KEY")
        print("   - ZHIPU_API_KEY")
        print("   - OPENROUTER_API_KEY")
        return
    
    print(f"✅ 已配置 {len(available)} 个供应商：\n")
    
    for provider_name in available:
        provider = manager.get_provider(provider_name)
        print(f"🔹 {provider_name.upper()}")
        print(f"   基础模型: {provider.default_model}")
        print(f"   推理模型: {provider.get_model(use_reasoner=True)}")
        print(f"   API地址: {provider.base_url}")
        print()

def main():
    """主演示函数"""
    print("\n" + "🎨 "*20)
    print("多LLM供应商功能演示")
    print("🎨 "*20)
    
    # 1. 显示可用模型
    demo_available_models()
    
    # 2. 演示不同Agent使用不同提供商
    demo_different_providers()
    
    # 3. 成本对比
    demo_cost_comparison()
    
    # 4. 配置指南
    demo_usage_guide()
    
    print("\n" + "="*70)
    print("✅ 演示完成！")
    print("="*70)
    print("\n💡 下一步：")
    print("   1. 在 .env 中配置您的API密钥")
    print("   2. 配置各Agent使用的提供商")
    print("   3. 运行 python main.py 开始使用")
    print("   4. 查看 LLM_PROVIDERS_GUIDE.md 了解更多详情")
    print()

if __name__ == '__main__':
    main()
