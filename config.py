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

# 系统配置
MAX_LOOP_COUNT = 3  # 默认最大循环次数
SEARCH_TIMEOUT = 10  # 搜索超时时间（秒）
MAX_SEARCH_RESULTS = 10  # 最大搜索结果数量
