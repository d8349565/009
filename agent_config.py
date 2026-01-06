"""
Agent模型配置文件
集中管理所有Agent使用的LLM提供商和模型配置

📋 配置说明：
- provider: LLM供应商 (deepseek/zhipu/glm/openrouter)
- model: 具体模型名称（None表示使用该供应商的默认模型）
- use_reasoner: 是否使用推理模型（影响模型选择）

💡 两种配置方式：
1. 【推荐】直接修改本文件的预设方案（第30-40行）
2. 在 .env 中配置环境变量（格式见下方说明）

🔧 .env 配置格式：
   # 格式1: 只指定供应商（使用默认模型）
   REQUIREMENT_ANALYZER_PROVIDER=glm
   
   # 格式2: 指定供应商和具体模型
   REQUIREMENT_ANALYZER_PROVIDER=glm
   REQUIREMENT_ANALYZER_MODEL=glm-4.7  # 新增！可以指定具体模型

⚙️ 配置优先级：
   .env中的 *_MODEL      （最高优先级）
   .env中的 *_PROVIDER
   agent_config.py预设方案
   默认值（兜底）
"""
import os

# ============================================================
# 配置方案选择
# ============================================================

# 💡 选择你想要使用的方案（取消注释即可）
# 注意：.env 中的环境变量优先级更高，会覆盖这里的设置

# 方案A: 经济型配置（全DeepSeek）
# 成本: ¥3-6 / 100次调用
# 适合: 个人用户、预算有限、日常使用
# AGENT_CONFIG_PRESET = "economy"

# 方案B: 混合型配置（推荐）⭐
# 成本: ¥6-10 / 100次调用  
# 适合: 商业用户、追求性价比、中文报告
# AGENT_CONFIG_PRESET = "balanced"

# 方案C: 高端配置
# 成本: ¥20-50 / 100次调用
# 适合: 关键报告、最高质量要求、英文内容
# AGENT_CONFIG_PRESET = "premium"

# 方案D: 自定义配置
# 使用下面的 AGENT_CONFIG_CUSTOM 配置
AGENT_CONFIG_PRESET = "custom"


# ============================================================
# 预设配置方案详情
# ============================================================

# 方案A: 经济型（全DeepSeek）
AGENT_CONFIG_ECONOMY = {
    "requirement_analyzer": {
        "provider": "deepseek",
        "model": "deepseek-chat",  # 明确指定模型
        "use_reasoner": False,
        "description": "快速分析用户需求"
    },
    "information_collector": {
        "provider": "deepseek",
        "model": "deepseek-chat",  # 明确指定模型
        "use_reasoner": False,
        "description": "批量评估搜索结果"
    },
    "report_writer": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 明确指定推理模型
        "use_reasoner": True,
        "description": "生成高质量报告（核心）"
    },
    "quality_judge": {
        "provider": "deepseek",
        "model": "deepseek-chat",  # 明确指定模型
        "use_reasoner": False,
        "description": "评估报告质量"
    },
    "comprehensive_report_writer": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 明确指定推理模型
        "use_reasoner": True,
        "description": "综合多个报告（深度分析）"
    }
}

# 方案B: 混合型（推荐）
AGENT_CONFIG_BALANCED = {
    "requirement_analyzer": {
        "provider": "glm",  # 或 zhipu
        "model": "glm-4-flash",  # 明确指定快速模型
        "use_reasoner": False,
        "description": "GLM中文理解更准确"
    },
    "information_collector": {
        "provider": "deepseek",
        "model": "deepseek-chat",  # 明确指定模型
        "use_reasoner": False,
        "description": "DeepSeek批量处理性价比高"
    },
    "report_writer": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 明确指定推理模型
        "use_reasoner": True,
        "description": "DeepSeek推理能力强"
    },
    "quality_judge": {
        "provider": "glm",
        "model": "glm-4-flash",  # 明确指定快速模型
        "use_reasoner": False,
        "description": "GLM快速评估"
    },
    "comprehensive_report_writer": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 明确指定推理模型
        "use_reasoner": True,
        "description": "DeepSeek深度推理"
    }
}

# 方案C: 高端配置
AGENT_CONFIG_PREMIUM = {
    "requirement_analyzer": {
        "provider": "glm",
        "model": "glm-4.7",  # 明确指定高级模型
        "use_reasoner": False,
        "description": "glm-4.7高级理解"
    },
    "information_collector": {
        "provider": "deepseek",
        "model": "deepseek-chat",  # 明确指定模型
        "use_reasoner": False,
        "description": "DeepSeek处理批量任务"
    },
    "report_writer": {
        "provider": "openrouter",
        "model": "xiaomi/mimo-v2-flash:free",  # 明确指定Claude 3.5
        "use_reasoner": False,
        "description": "Claude 3.5顶级写作"
    },
    "quality_judge": {
        "provider": "glm",
        "model": "glm-4.7",
        "use_reasoner": False,
        "description": "glm-4.7严格评审"
    },
    "comprehensive_report_writer": {
        "provider": "openrouter",
        "model": "openai/o1-preview",  # 明确指定O1推理模型
        "use_reasoner": False,
        "description": "O1顶级推理"
    }
}

# 方案D: 自定义配置（你可以自己修改）
AGENT_CONFIG_CUSTOM = {
    "requirement_analyzer": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 指定具体模型
        "use_reasoner": True,
        "description": "思索用户需求"
    },
    "information_collector": {
        "provider": "openrouter",
        "model": "xiaomi/mimo-v2-flash:free",  # 指定具体模型
        "use_reasoner": False,
        "description": "信息收集，要便宜"
    },
    "report_writer": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 指定具体模型
        "use_reasoner": True,
        "description": "思索报告内容"
    },
    "quality_judge": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 指定具体模型
        "use_reasoner": True,
        "description": "自定义配置"
    },
    "comprehensive_report_writer": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",  # 指定具体模型
        "use_reasoner": True,
        "description": "自定义配置"
    }
}


# ============================================================
# 获取当前激活的配置
# ============================================================

def get_active_agent_config():
    """
    获取当前激活的Agent配置
    
    优先级（从高到低）：
    1. 环境变量中的具体模型 (*_MODEL)  
    2. 环境变量中的供应商 (*_PROVIDER)
    3. 预设方案 (AGENT_CONFIG_PRESET)
    4. 默认配置
    
    支持的环境变量格式：
    - REQUIREMENT_ANALYZER_PROVIDER=glm        # 只指定供应商
    - REQUIREMENT_ANALYZER_MODEL=glm-4.7    # 指定具体模型（可选）
    
    Returns:
        dict: Agent配置字典
    """
    # 选择预设方案
    config_map = {
        "economy": AGENT_CONFIG_ECONOMY,
        "balanced": AGENT_CONFIG_BALANCED,
        "premium": AGENT_CONFIG_PREMIUM,
        "custom": AGENT_CONFIG_CUSTOM
    }
    
    active_config = config_map.get(AGENT_CONFIG_PRESET, AGENT_CONFIG_ECONOMY)
    
    # 环境变量覆盖（优先级最高）
    final_config = {}
    for agent_key, agent_settings in active_config.items():
        # 环境变量名称（转换为大写并加前缀）
        provider_env_var = f"{agent_key.upper()}_PROVIDER"
        model_env_var = f"{agent_key.upper()}_MODEL"
        
        # 从环境变量读取供应商和模型
        env_provider = os.getenv(provider_env_var)
        env_model = os.getenv(model_env_var)
        
        if env_provider or env_model:
            # 使用环境变量配置（优先级最高）
            final_provider = env_provider or agent_settings.get("provider")
            final_model = env_model or agent_settings.get("model")
            
            source_desc = []
            if env_provider:
                source_desc.append(f"供应商从.env")
            if env_model:
                source_desc.append(f"模型从.env")
            
            source_info = f" [{', '.join(source_desc)}]" if source_desc else ""
            
            final_config[agent_key] = {
                "provider": final_provider,
                "model": final_model,
                "use_reasoner": agent_settings.get("use_reasoner", False),
                "description": f"{agent_settings.get('description', '')}{source_info}"
            }
        else:
            # 使用预设配置
            final_config[agent_key] = agent_settings
    
    return final_config


def print_current_config():
    """打印当前激活的配置（改进版 - 更清晰的显示）"""
    config = get_active_agent_config()
    
    print("\n" + "="*80)
    print(f"📋 当前Agent配置方案: {AGENT_CONFIG_PRESET.upper()}")
    print("="*80)
    
    # 添加表头
    print(f"\n{'Agent名称':<25} {'供应商':<12} {'模型':<25} {'推理':<6} {'说明'}")
    print("-" * 80)
    
    for agent_key, settings in config.items():
        # Agent名称（中文）
        agent_names = {
            "requirement_analyzer": "需求分析师",
            "information_collector": "信息收集员",
            "report_writer": "报告撰写员",
            "quality_judge": "质量评审员",
            "comprehensive_report_writer": "综合报告撰写员"
        }
        agent_name = agent_names.get(agent_key, agent_key)
        
        provider = settings['provider'].upper()
        model = settings.get('model') or '(自动选择)'
        reasoner = "是" if settings.get('use_reasoner') else "否"
        desc = settings.get('description', '')
        
        # 格式化输出（对齐）
        print(f"{agent_name:<20} {provider:<12} {model:<25} {reasoner:<6} {desc[:30]}")
    
    print("\n" + "="*80)
    print("💡 配置说明：")
    print("   - 模型显示 '(自动选择)' 表示使用该供应商的默认模型")
    print("   - 推理模式 '是' 表示使用推理模型（如deepseek-reasoner）")
    print("\n� 如何修改配置：")
    print("   方式1: 修改本文件的 AGENT_CONFIG_PRESET 变量（推荐）")
    print("   方式2: 在 .env 中配置环境变量（优先级更高）")
    print("          格式: REQUIREMENT_ANALYZER_PROVIDER=glm")
    print("          格式: REQUIREMENT_ANALYZER_MODEL=glm-4.7  # 可选，指定具体模型")
    print("\n📖 查看详细说明: 运行 'python agent_config.py'")
    print("="*80 + "\n")
    print("   - 运行 'python agent_config.py' 查看当前配置")
    print("="*70 + "\n")


# ============================================================
# 成本估算
# ============================================================

COST_ESTIMATE = {
    "economy": {
        "cost_per_100": "¥3-6",
        "description": "最经济，适合日常使用"
    },
    "balanced": {
        "cost_per_100": "¥6-10",
        "description": "性价比最优，推荐使用"
    },
    "premium": {
        "cost_per_100": "¥20-50",
        "description": "最高质量，关键报告使用"
    },
    "custom": {
        "cost_per_100": "取决于配置",
        "description": "自定义方案"
    }
}


def print_cost_estimate():
    """打印成本估算"""
    print("\n" + "="*70)
    print("💰 成本估算")
    print("="*70 + "\n")
    
    for preset, info in COST_ESTIMATE.items():
        marker = "👉" if preset == AGENT_CONFIG_PRESET else "  "
        print(f"{marker} {preset.upper()}: {info['cost_per_100']} / 100次调用")
        print(f"   {info['description']}\n")
    
    print("="*70 + "\n")


# ============================================================
# 主程序：显示当前配置
# ============================================================

if __name__ == "__main__":
    print("\n🎨 Agent模型配置管理器\n")
    print_current_config()
    print_cost_estimate()
    
    print("📋 如何修改配置：")
    print("   1. 编辑本文件，修改 AGENT_CONFIG_PRESET 变量")
    print("   2. 或编辑 .env 文件中的 *_PROVIDER 变量")
    print("   3. 保存后重新运行程序即可生效\n")
