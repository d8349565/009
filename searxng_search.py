import requests
import json
import argparse
from typing import Dict, List, Any
from collections import defaultdict
import time

class SearXNGSearch:
    def __init__(self, base_url: str = "https://ldgogogo.cn:18080"):
        """
        初始化SearXNG搜索客户端
        
        Args:
            base_url: SearXNG实例的基础URL，默认为 https://ldgogogo.cn:18080
        """
        self.base_url = base_url.rstrip('/')
        self.search_url = f"{self.base_url}/search"
        
    def search(self, query: str, 
               engines: List[str] = None,
               categories: List[str] = None,
               language: str = "zh-CN",
               format: str = "json",
               pageno: int = 1,
               timeout: int = 30) -> Dict[str, Any]:
        """
        执行搜索请求
        
        Args:
            query: 搜索关键词
            engines: 指定使用的搜索引擎列表，如 ["google", "bing", "baidu"]
            categories: 搜索类别，如 ["general", "images", "news"]
            language: 语言代码，默认为中文
            format: 返回格式，默认为json
            pageno: 页码，默认为1
            timeout: 请求超时时间（秒）
            
        Returns:
            包含搜索结果的字典
        """
        params = {
            "q": query,
            "format": format,
            "pageno": pageno,
            "language": language,
        }
        
        if engines:
            params["engines"] = ",".join(engines)
        if categories:
            params["categories"] = ",".join(categories)
        
        try:
            response = requests.get(
                self.search_url,
                params=params,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"搜索请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None
    
    def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析搜索结果，统计各引擎返回的结果数量
        
        Args:
            results: SearXNG返回的搜索结果
            
        Returns:
            包含统计信息的字典
        """
        if not results:
            return {"error": "无有效结果"}
        
        analysis = {
            "query": results.get("query", ""),
            "number_of_results": results.get("number_of_results", 0),
            "results": [],
            "engine_stats": defaultdict(int),
            "category_stats": defaultdict(int),
            "total_results": 0
        }
        
        # 统计各引擎结果数量
        for result in results.get("results", []):
            engine = result.get("engine", "unknown")
            category = result.get("category", "unknown")
            
            analysis["engine_stats"][engine] += 1
            analysis["category_stats"][category] += 1
            analysis["total_results"] += 1
            
            # 收集结果信息
            result_info = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "engine": engine,
                "category": category,
                "score": result.get("score", 0)
            }
            analysis["results"].append(result_info)
        
        return analysis
    
    def print_statistics(self, analysis: Dict[str, Any], show_details: bool = False):
        """
        打印统计信息
        
        Args:
            analysis: 分析结果
            show_details: 是否显示详细结果
        """
        if "error" in analysis:
            print(f"错误: {analysis['error']}")
            return
        
        print("=" * 80)
        print(f"搜索关键词: {analysis['query']}")
        print(f"总结果数: {analysis['total_results']}")
        print(f"预估总结果数: {analysis.get('number_of_results', 0)}")
        print("-" * 80)
        
        # 打印引擎统计
        print("\n📊 搜索引擎统计:")
        print("-" * 40)
        for engine, count in sorted(analysis["engine_stats"].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / analysis["total_results"] * 100) if analysis["total_results"] > 0 else 0
            print(f"  {engine:20s}: {count:3d} 条结果 ({percentage:.1f}%)")
        
        # 打印类别统计
        print("\n📁 类别统计:")
        print("-" * 40)
        for category, count in sorted(analysis["category_stats"].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / analysis["total_results"] * 100) if analysis["total_results"] > 0 else 0
            print(f"  {category:20s}: {count:3d} 条结果 ({percentage:.1f}%)")
        
        # 打印详细结果
        if show_details and analysis["results"]:
            print("\n🔍 详细结果:")
            print("-" * 80)
            for i, result in enumerate(analysis["results"], 1):
                print(f"{i:3d}. [{result['engine']:10s}] {result['title'][:60]}...")
                print(f"     URL: {result['url']}")
                print(f"     类别: {result['category']}, 评分: {result['score']}")
                print()
        
        print("=" * 80)
    
    def search_and_analyze(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        执行搜索并分析结果
        
        Args:
            query: 搜索关键词
            **kwargs: 传递给search方法的其他参数
            
        Returns:
            分析结果
        """
        print(f"🔎 正在搜索: {query}")
        start_time = time.time()
        
        results = self.search(query, **kwargs)
        if results is None:
            return {"error": "搜索失败"}
        
        analysis = self.analyze_results(results)
        elapsed_time = time.time() - start_time
        
        analysis["search_time"] = elapsed_time
        print(f"⏱️  搜索耗时: {elapsed_time:.2f} 秒")
        
        return analysis

def main():
    parser = argparse.ArgumentParser(description="SearXNG搜索客户端")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--url", default="https://ldgogogo.cn:18080", 
                       help="SearXNG实例URL (默认: https://ldgogogo.cn:18080)")
    parser.add_argument("--engines", nargs="+", 
                       help="指定搜索引擎，如: google bing baidu")
    parser.add_argument("--categories", nargs="+", 
                       help="指定搜索类别，如: general images news")
    parser.add_argument("--language", default="zh-CN", 
                       help="语言代码 (默认: zh-CN)")
    parser.add_argument("--details", action="store_true", 
                       help="显示详细结果")
    parser.add_argument("--pageno", type=int, default=1, 
                       help="页码 (默认: 1)")
    
    args = parser.parse_args()
    
    # 创建搜索客户端
    searxng = SearXNGSearch(args.url)
    
    # 执行搜索
    analysis = searxng.search_and_analyze(
        query=args.query,
        engines=args.engines,
        categories=args.categories,
        language=args.language,
        pageno=args.pageno
    )
    
    # 打印统计信息
    searxng.print_statistics(analysis, show_details=args.details)

if __name__ == "__main__":
    main()