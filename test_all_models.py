"""
测试所有模型连接性
验证各个LLM供应商和模型是否正常工作

使用方法:
python test_all_models.py
"""

import os
from dotenv import load_dotenv
from llm_providers import LLMProviderManager

# 加载环境变量
load_dotenv()

def print_section(title):
    """打印分隔线"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_provider(provider_name, model_name=None):
    """
    测试单个供应商的模型
    
    Args:
        provider_name: 供应商名称 (deepseek/glm/zhipu/openrouter)
        model_name: 具体模型名称（可选）
    """
    print(f"📡 正在测试: {provider_name.upper()}", end="")
    if model_name:
        print(f" - {model_name}")
    else:
        print(" (默认模型)")
    
    try:
        # 创建provider manager
        manager = LLMProviderManager()
        
        # 获取provider实例
        provider = manager.get_provider(provider_name)
        
        # 测试对话（简单问题）
        test_prompt = "请用一句话介绍你自己。"
        
        print(f"   提问: {test_prompt}")
        print(f"   回答: ", end="", flush=True)
                
        # 构造消息列表
        messages = [
            {"role": "system", "content": "你是一个AI助手。"},
            {"role": "user", "content": test_prompt}
        ]
        
        # 调用API（指定模型）
        response = provider.call(
            messages=messages,
            model=model_name  # 传入具体模型名称
        )
        
        # 打印响应
        print(f"{response[:100]}..." if len(response) > 100 else response)
        
        print("   ✅ 连接成功！\n")
        return True
        
    except Exception as e:
        print(f"   ❌ 连接失败: {str(e)}\n")
        return False


def check_api_keys():
    """检查API密钥配置"""
    print_section("🔑 检查API密钥配置")
    
    api_keys = {
        "DeepSeek": "DEEPSEEK_API_KEY",
        "智谱AI (GLM)": "ZHIPU_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY"
    }
    
    configured = []
    missing = []
    
    for name, env_var in api_keys.items():
        key = os.getenv(env_var)
        if key and key != f"your_{env_var.lower()}_here":
            configured.append(name)
            print(f"✅ {name:<20} - 已配置")
        else:
            missing.append(name)
            print(f"❌ {name:<20} - 未配置 (环境变量: {env_var})")
    
    print(f"\n📊 总结: {len(configured)}/{len(api_keys)} 个供应商已配置")
    
    if missing:
        print(f"⚠️  缺失的供应商: {', '.join(missing)}")
        print(f"💡 提示: 在 .env 文件中配置相应的API密钥\n")
    
    return configured


def main():
    """主测试流程"""
    print("\n" + "🚀 " + "="*76)
    print("  LLM模型连接性测试工具")
    print("="*78 + "\n")
    
    # 1. 检查API密钥
    configured_providers = check_api_keys()
    
    if not configured_providers:
        print("❌ 没有配置任何API密钥，无法进行测试")
        print("💡 请先在 .env 文件中配置至少一个供应商的API密钥\n")
        return
    
    # 2. 测试各个供应商和模型
    print_section("🧪 开始模型连接测试")
    
    test_results = {}
    
    # DeepSeek 测试
    if "DeepSeek" in configured_providers:
        print("┌─ DeepSeek 供应商 ─────────────────────────────────────────┐\n")
        
        test_results["deepseek-chat"] = test_provider("deepseek", "deepseek-chat")
        test_results["deepseek-reasoner"] = test_provider("deepseek", "deepseek-reasoner")
        
        print("└────────────────────────────────────────────────────────────┘")
    
    # 智谱AI (GLM) 测试
    if "智谱AI (GLM)" in configured_providers:
        print("\n┌─ 智谱AI (GLM) 供应商 ─────────────────────────────────────┐\n")
        
        # 测试两种provider名称（glm 和 zhipu 都支持）
        test_results["glm-4.7"] = test_provider("glm", "glm-4.7")
        test_results["glm-4.7"] = test_provider("glm", "glm-4.7")
        
        print("└────────────────────────────────────────────────────────────┘")
    
    # OpenRouter 测试
    if "OpenRouter" in configured_providers:
        print("\n┌─ OpenRouter 供应商 ───────────────────────────────────────┐\n")
        
        test_results["xiaomi/mimo-v2-flash:free"] = test_provider("openrouter", "xiaomi/mimo-v2-flash:free")
        
        # O1模型测试（如果需要）
        # test_results["o1-preview"] = test_provider("openrouter", "openai/o1-preview")
        
        print("└────────────────────────────────────────────────────────────┘")
    
    # 3. 测试总结
    print_section("📊 测试结果总结")
    
    success_count = sum(1 for result in test_results.values() if result)
    total_count = len(test_results)
    
    print(f"✅ 成功: {success_count}/{total_count} 个模型")
    print(f"❌ 失败: {total_count - success_count}/{total_count} 个模型\n")
    
    if success_count == total_count:
        print("🎉 所有模型连接正常！可以开始使用系统了。\n")
    elif success_count > 0:
        print("⚠️  部分模型连接失败，请检查：")
        print("   1. API密钥是否正确")
        print("   2. 网络连接是否正常")
        print("   3. API额度是否充足")
        print("   4. 模型名称是否正确\n")
    else:
        print("❌ 所有模型连接失败，请检查：")
        print("   1. .env 文件中的API密钥是否正确")
        print("   2. API密钥是否有效（未过期）")
        print("   3. 网络连接是否正常\n")
    
    # 4. 详细结果
    print("详细结果:")
    print("-" * 80)
    for model, result in test_results.items():
        status = "✅ 成功" if result else "❌ 失败"
        print(f"  {model:<30} {status}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  测试已中断\n")
    except Exception as e:
        print(f"\n❌ 测试过程出错: {str(e)}\n")
