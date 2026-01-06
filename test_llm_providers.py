#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试多LLM供应商功能
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from llm_providers import get_llm_manager
from agents import RequirementAnalyzer, ReportWriter
import config

def test_provider_manager():
    """测试供应商管理器"""
    print("="*60)
    print("测试1: 供应商管理器")
    print("="*60)
    
    manager = get_llm_manager()
    available = manager.get_available_providers()
    
    print(f"✓ 已配置的供应商: {', '.join(available)}")
    print()
    
    # 测试每个供应商
    for provider_name in available:
        provider = manager.get_provider(provider_name)
        if provider:
            print(f"✓ {provider_name.upper()}")
            print(f"  - 基础模型: {provider.default_model}")
            print(f"  - 推理模型: {provider.get_model(use_reasoner=True)}")
        else:
            print(f"✗ {provider_name.upper()} 不可用")
    print()

def test_agent_provider():
    """测试Agent使用不同提供商"""
    print("="*60)
    print("测试2: Agent提供商配置")
    print("="*60)
    
    # 测试需求分析师
    print(f"\n需求分析师配置:")
    print(f"  - 配置的提供商: {config.REQUIREMENT_ANALYZER_PROVIDER}")
    
    analyzer = RequirementAnalyzer()
    print(f"  - 实际使用: {analyzer.provider_name}")
    
    # 测试报告撰写员
    print(f"\n报告撰写员配置:")
    print(f"  - 配置的提供商: {config.REPORT_WRITER_PROVIDER}")
    
    writer = ReportWriter()
    print(f"  - 实际使用: {writer.provider_name}")
    print(f"  - 使用推理模式: {writer.use_reasoner}")
    print()

def test_simple_call():
    """测试简单API调用"""
    print("="*60)
    print("测试3: 实际API调用")
    print("="*60)
    
    manager = get_llm_manager()
    available = manager.get_available_providers()
    
    if not available:
        print("✗ 没有可用的提供商，请配置API密钥")
        return
    
    # 选择第一个可用的提供商进行测试
    test_provider = available[0]
    print(f"\n使用 {test_provider.upper()} 进行测试...")
    
    try:
        messages = [
            {"role": "system", "content": "你是一个友好的助手。"},
            {"role": "user", "content": "请用一句话介绍你自己。"}
        ]
        
        response = manager.call_llm(
            provider_name=test_provider,
            messages=messages,
            temperature=0.7
        )
        
        print(f"\n✓ API调用成功！")
        print(f"响应: {response[:200]}...")
        
    except Exception as e:
        print(f"\n✗ API调用失败: {e}")
        print(f"请检查 {test_provider.upper()} 的API密钥是否正确配置")
    
    print()

def test_provider_fallback():
    """测试提供商回退机制"""
    print("="*60)
    print("测试4: 提供商回退机制")
    print("="*60)
    
    # 尝试使用不存在的提供商
    print("\n尝试使用不存在的提供商 'invalid_provider'...")
    
    analyzer = RequirementAnalyzer(provider="invalid_provider")
    print(f"✓ 自动回退到: {analyzer.provider_name}")
    print()

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("多LLM供应商功能测试")
    print("="*60 + "\n")
    
    try:
        # 测试1: 供应商管理器
        test_provider_manager()
        
        # 测试2: Agent配置
        test_agent_provider()
        
        # 测试3: 简单API调用
        test_simple_call()
        
        # 测试4: 回退机制
        test_provider_fallback()
        
        print("="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        
        # 显示配置建议
        manager = get_llm_manager()
        available = manager.get_available_providers()
        
        if len(available) == 1:
            print("\n💡 提示: 您只配置了1个供应商")
            print("   可以在 .env 中添加更多供应商以实现负载均衡")
            print("   支持: DEEPSEEK_API_KEY, ZHIPU_API_KEY, OPENROUTER_API_KEY")
        elif len(available) > 1:
            print(f"\n✨ 您已配置 {len(available)} 个供应商，可以灵活切换！")
            print("   在 .env 中配置 *_PROVIDER 变量来指定每个Agent使用的提供商")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
