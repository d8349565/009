"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = "deepseek-chat"  # 普通聊天模型
DEEPSEEK_REASONER = "deepseek-reasoner"  # 思考模式（推理模型）

# SearXNG搜索引擎配置
SEARXNG_ENABLED = os.getenv("SEARXNG_ENABLED", "false").lower() == "true"
SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "http://localhost:8080")
SEARXNG_API_KEY = os.getenv("SEARXNG_API_KEY", "")

# Tavily搜索引擎配置
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
TAVILY_ENABLED = os.getenv("TAVILY_ENABLED", "false").lower() == "true"

# 搜索引擎选择：'searxng', 'tavily'
SEARCH_ENGINE_TYPE = os.getenv("SEARCH_ENGINE_TYPE", "searxng")

# 系统配置
MAX_LOOP_COUNT = 1  # 默认最大循环次数
SEARCH_TIMEOUT = 10  # 搜索超时时间（秒）
MAX_SEARCH_RESULTS = 20  # 最大搜索结果数量

# 优先搜索源配置
PRIORITY_SOURCES = {
    "enabled": False,  # 是否启用优先搜索源（默认关闭，由用户在启动时选择）
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
