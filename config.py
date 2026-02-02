"""
配置文件
"""
import os
from dotenv import load_dotenv
from runtime_config import load_runtime_config, get_nested, parse_bool

# 加载环境变量
load_dotenv()

RUNTIME_CONFIG = load_runtime_config()

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

def _runtime_agent(agent_key: str) -> dict:
    agents_cfg = get_nested(RUNTIME_CONFIG, ["agents"], {}) or {}
    if not isinstance(agents_cfg, dict):
        return {}
    agent_cfg = agents_cfg.get(agent_key, {})
    return agent_cfg if isinstance(agent_cfg, dict) else {}


def _agent_provider(agent_key: str, env_prefix: str, default: str = "deepseek") -> str:
    base = _runtime_agent(agent_key).get("provider") or default
    return (os.getenv(f"{env_prefix}_PROVIDER") or base or default).strip()


def _agent_model(agent_key: str, env_prefix: str, default: str = "") -> str:
    base = _runtime_agent(agent_key).get("model") or default
    return (os.getenv(f"{env_prefix}_MODEL") or base or default).strip()


def _agent_use_reasoner(agent_key: str, env_prefix: str, default: bool = False) -> bool:
    base = bool(_runtime_agent(agent_key).get("use_reasoner", default))
    return parse_bool(os.getenv(f"{env_prefix}_USE_REASONER"), base)


REQUIREMENT_ANALYZER_PROVIDER = _agent_provider("requirement_analyzer", "REQUIREMENT_ANALYZER", "deepseek")
REQUIREMENT_ANALYZER_MODEL = _agent_model("requirement_analyzer", "REQUIREMENT_ANALYZER", "")
REQUIREMENT_ANALYZER_USE_REASONER = _agent_use_reasoner("requirement_analyzer", "REQUIREMENT_ANALYZER", False)

INFORMATION_COLLECTOR_PROVIDER = _agent_provider("information_collector", "INFORMATION_COLLECTOR", "deepseek")
INFORMATION_COLLECTOR_MODEL = _agent_model("information_collector", "INFORMATION_COLLECTOR", "")
INFORMATION_COLLECTOR_USE_REASONER = _agent_use_reasoner("information_collector", "INFORMATION_COLLECTOR", False)

REPORT_WRITER_PROVIDER = _agent_provider("report_writer", "REPORT_WRITER", "deepseek")
REPORT_WRITER_MODEL = _agent_model("report_writer", "REPORT_WRITER", "")
REPORT_WRITER_USE_REASONER = _agent_use_reasoner("report_writer", "REPORT_WRITER", True)

QUALITY_JUDGE_PROVIDER = _agent_provider("quality_judge", "QUALITY_JUDGE", "deepseek")
QUALITY_JUDGE_MODEL = _agent_model("quality_judge", "QUALITY_JUDGE", "")
QUALITY_JUDGE_USE_REASONER = _agent_use_reasoner("quality_judge", "QUALITY_JUDGE", False)

COMPREHENSIVE_REPORT_WRITER_PROVIDER = _agent_provider("comprehensive_report_writer", "COMPREHENSIVE_REPORT_WRITER", "deepseek")
COMPREHENSIVE_REPORT_WRITER_MODEL = _agent_model("comprehensive_report_writer", "COMPREHENSIVE_REPORT_WRITER", "")
COMPREHENSIVE_REPORT_WRITER_USE_REASONER = _agent_use_reasoner("comprehensive_report_writer", "COMPREHENSIVE_REPORT_WRITER", True)

_runtime_search = get_nested(RUNTIME_CONFIG, ["search"], {}) or {}
if not isinstance(_runtime_search, dict):
    _runtime_search = {}
_runtime_logging = get_nested(RUNTIME_CONFIG, ["logging"], {}) or {}
if not isinstance(_runtime_logging, dict):
    _runtime_logging = {}

# SearXNG搜索引擎配置
SEARXNG_ENABLED = os.getenv("SEARXNG_ENABLED", "false").lower() == "true"
SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "http://localhost:8080")
SEARXNG_API_KEY = os.getenv("SEARXNG_API_KEY", "")

# Tavily搜索引擎配置
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_ENABLED = os.getenv("TAVILY_ENABLED", "false").lower() == "true"

# 搜索引擎选择：'searxng', 'tavily'
SEARCH_ENGINE_TYPE = os.getenv("SEARCH_ENGINE_TYPE", str(_runtime_search.get("engine_type", "searxng")))

# 搜索模式配置
# SEARCH_MODE: 'quick' (快速搜索模式，一次搜索直接生成报告) 或 'full' (完整搜索模式，多轮迭代优化)
SEARCH_MODE = os.getenv("SEARCH_MODE", str(_runtime_search.get("mode", "quick")))

# 系统配置
MAX_LOOP_COUNT = int(os.getenv("MAX_LOOP_COUNT", str(_runtime_search.get("max_loop_count", 1))))
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", str(_runtime_search.get("timeout", 10))))
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", str(_runtime_search.get("max_results", 30))))

# 性能优化配置
SKIP_EVALUATION = parse_bool(os.getenv("SKIP_EVALUATION"), bool(_runtime_search.get("skip_evaluation", False)))
SIMPLIFY_REPORT_INPUT = parse_bool(os.getenv("SIMPLIFY_REPORT_INPUT"), bool(_runtime_search.get("simplify_report_input", False)))

# 数据提取配置
# 控制发送给AI评估的内容长度（字符数）
# 500 = 极速但数据不完整
# 1500 = 均衡（推荐）
# 3000 = 数据完整但较慢
# 5000 = 最完整但最慢
CONTENT_EXTRACT_LENGTH = int(os.getenv("CONTENT_EXTRACT_LENGTH", str(_runtime_search.get("content_extract_length", 2000))))

# å†…å®¹æŠ“å–é…ç½®
FETCH_RETRY_TOTAL = int(os.getenv("FETCH_RETRY_TOTAL", "2"))
FETCH_BACKOFF_FACTOR = float(os.getenv("FETCH_BACKOFF_FACTOR", "0.5"))

# 并发评估配置
# 控制同时评估的批次数量，提高评估速度
# 1 = 串行（最安全）
# 3 = 并发3批（推荐，提速70%）
# 5 = 并发5批（激进，提速75%，可能触发限流）
MAX_CONCURRENT_EVALUATIONS = int(os.getenv("MAX_CONCURRENT_EVALUATIONS", str(_runtime_search.get("max_concurrent_evaluations", 3))))

# 优先搜索源开关（是否启用权威机构优先搜索）
USE_PRIORITY_SOURCES = parse_bool(os.getenv("USE_PRIORITY_SOURCES"), bool(_runtime_search.get("use_priority_sources", False)))

# 智能停止配置
# 首轮报告质量满足时是否自动停止（不继续迭代）
EARLY_STOP_ON_SATISFACTION = parse_bool(os.getenv("EARLY_STOP_ON_SATISFACTION"), bool(_runtime_search.get("early_stop_on_satisfaction", True)))

# ============================================================
# 日志输出配置
# ============================================================
# 控制日志输出的详细程度
# verbose   - 详细模式，显示所有日志（包括API调用详情、提供商信息等）
# normal    - 正常模式，显示关键步骤和结果（推荐）
# minimal   - 精简模式，只显示核心进度和最终结果
LOG_LEVEL = os.getenv("LOG_LEVEL", str(_runtime_logging.get("level", "normal"))).lower()

# 是否在控制台打印最终报告内容
PRINT_FINAL_REPORT = parse_bool(os.getenv("PRINT_FINAL_REPORT"), bool(_runtime_logging.get("print_final_report", False)))

FETCH_FAILURE_LOG_MODE = os.getenv("FETCH_FAILURE_LOG_MODE", str(_runtime_logging.get("fetch_failure_log_mode", "summary"))).lower()

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
