"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============================================================
# LLM供应商配置
# ============================================================

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = "deepseek-chat"  # 普通聊天模型
DEEPSEEK_REASONER = "deepseek-reasoner"  # 思考模式（推理模型）

# 智谱AI (GLM) 配置
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

# OpenRouter 配置（聚合多个模型）
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "xiaomi/mimo-v2-flash:free")
OPENROUTER_REASONER_MODEL = os.getenv("OPENROUTER_REASONER_MODEL", "openai/o1-preview")

# ============================================================
# Agent模型配置 - 为每个Agent指定使用的提供商
# ============================================================
# 
# 💡 配置方式（按优先级）：
# 1. 环境变量 (.env文件) - 最高优先级
# 2. agent_config.py 预设方案 - 推荐使用
# 3. 下面的默认值 - 兜底配置
#
# 📝 推荐：直接修改 agent_config.py 文件选择预设方案
#    运行 'python agent_config.py' 查看当前配置
#
# 可选值: 'deepseek', 'zhipu'/'glm', 'openrouter'

# 尝试从 agent_config.py 加载配置
try:
    from agent_config import get_active_agent_config
    _agent_config = get_active_agent_config()
    
    # 需求分析师
    REQUIREMENT_ANALYZER_PROVIDER = os.getenv(
        "REQUIREMENT_ANALYZER_PROVIDER",
        _agent_config.get("requirement_analyzer", {}).get("provider", "deepseek")
    )
    
    # 信息收集员
    INFORMATION_COLLECTOR_PROVIDER = os.getenv(
        "INFORMATION_COLLECTOR_PROVIDER",
        _agent_config.get("information_collector", {}).get("provider", "deepseek")
    )
    
    # 报告撰写员
    REPORT_WRITER_PROVIDER = os.getenv(
        "REPORT_WRITER_PROVIDER",
        _agent_config.get("report_writer", {}).get("provider", "deepseek")
    )
    
    # 质量评审员
    QUALITY_JUDGE_PROVIDER = os.getenv(
        "QUALITY_JUDGE_PROVIDER",
        _agent_config.get("quality_judge", {}).get("provider", "deepseek")
    )
    
    # 综合报告撰写员
    COMPREHENSIVE_REPORT_WRITER_PROVIDER = os.getenv(
        "COMPREHENSIVE_REPORT_WRITER_PROVIDER",
        _agent_config.get("comprehensive_report_writer", {}).get("provider", "deepseek")
    )
    
except ImportError:
    # 如果 agent_config.py 不存在，使用默认配置
    REQUIREMENT_ANALYZER_PROVIDER = os.getenv("REQUIREMENT_ANALYZER_PROVIDER", "deepseek")
    INFORMATION_COLLECTOR_PROVIDER = os.getenv("INFORMATION_COLLECTOR_PROVIDER", "deepseek")
    REPORT_WRITER_PROVIDER = os.getenv("REPORT_WRITER_PROVIDER", "deepseek")
    QUALITY_JUDGE_PROVIDER = os.getenv("QUALITY_JUDGE_PROVIDER", "deepseek")
    COMPREHENSIVE_REPORT_WRITER_PROVIDER = os.getenv("COMPREHENSIVE_REPORT_WRITER_PROVIDER", "deepseek")

# SearXNG搜索引擎配置
SEARXNG_ENABLED = os.getenv("SEARXNG_ENABLED", "false").lower() == "true"
SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "http://localhost:8080")
SEARXNG_API_KEY = os.getenv("SEARXNG_API_KEY", "")

# Tavily搜索引擎配置
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_ENABLED = os.getenv("TAVILY_ENABLED", "false").lower() == "true"

# 搜索引擎选择：'searxng', 'tavily'
SEARCH_ENGINE_TYPE = os.getenv("SEARCH_ENGINE_TYPE", "searxng")

# 搜索模式配置
# SEARCH_MODE: 'quick' (快速搜索模式，一次搜索直接生成报告) 或 'full' (完整搜索模式，多轮迭代优化)
SEARCH_MODE = os.getenv("SEARCH_MODE", "quick")

# 系统配置
MAX_LOOP_COUNT = int(os.getenv("MAX_LOOP_COUNT", "1"))  # 完整搜索模式的最大循环次数
SEARCH_TIMEOUT = 10  # 搜索超时时间（秒）
MAX_SEARCH_RESULTS = 30  # 最大搜索结果数量

# 性能优化配置
SKIP_EVALUATION = os.getenv("SKIP_EVALUATION", "false").lower() == "true"  # 是否跳过信息评估环节（极速模式）
SIMPLIFY_REPORT_INPUT = os.getenv("SIMPLIFY_REPORT_INPUT", "false").lower() == "true"  # 是否精简报告生成的输入数据

# 数据提取配置
# 控制发送给AI评估的内容长度（字符数）
# 500 = 极速但数据不完整
# 1500 = 均衡（推荐）
# 3000 = 数据完整但较慢
# 5000 = 最完整但最慢
CONTENT_EXTRACT_LENGTH = int(os.getenv("CONTENT_EXTRACT_LENGTH", "2000"))

# å†…å®¹æŠ“å–é…ç½®
FETCH_RETRY_TOTAL = int(os.getenv("FETCH_RETRY_TOTAL", "2"))
FETCH_BACKOFF_FACTOR = float(os.getenv("FETCH_BACKOFF_FACTOR", "0.5"))

# 并发评估配置
# 控制同时评估的批次数量，提高评估速度
# 1 = 串行（最安全）
# 3 = 并发3批（推荐，提速70%）
# 5 = 并发5批（激进，提速75%，可能触发限流）
MAX_CONCURRENT_EVALUATIONS = int(os.getenv("MAX_CONCURRENT_EVALUATIONS", "3"))

# 优先搜索源开关（是否启用权威机构优先搜索）
USE_PRIORITY_SOURCES = os.getenv("USE_PRIORITY_SOURCES", "false").lower() == "true"

# 智能停止配置
# 首轮报告质量满足时是否自动停止（不继续迭代）
EARLY_STOP_ON_SATISFACTION = os.getenv("EARLY_STOP_ON_SATISFACTION", "true").lower() == "true"

# ============================================================
# 日志输出配置
# ============================================================
# 控制日志输出的详细程度
# verbose   - 详细模式，显示所有日志（包括API调用详情、提供商信息等）
# normal    - 正常模式，显示关键步骤和结果（推荐）
# minimal   - 精简模式，只显示核心进度和最终结果
LOG_LEVEL = os.getenv("LOG_LEVEL", "normal").lower()

# 是否在控制台打印最终报告内容
PRINT_FINAL_REPORT = os.getenv("PRINT_FINAL_REPORT", "false").lower() == "true"

# 优先搜索源配置
PRIORITY_SOURCES = {
    "enabled": USE_PRIORITY_SOURCES,  # 使用环境变量控制
    "organizations": [
        # 权威研究机构
        
        # 官方统计/协会
        "中国涂料工业协会",
        "中国国家统计局",
        "国家统计局",
        
        # 专业行业媒体
        "涂界",

        
        # 国际咨询机构

    ],
    "keywords_boost": [
        # 添加这些关键词到搜索查询以优先匹配权威源

    ]
}
