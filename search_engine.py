"""
搜索和信息获取模块
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import config


class SearchEngine:
    """搜索引擎封装"""
    
    def __init__(self):
        self.timeout = config.SEARCH_TIMEOUT
        self.max_results = config.MAX_SEARCH_RESULTS
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search(self, keywords: List[str]) -> List[Dict[str, str]]:
        """
        执行搜索
        如果启用了SearXNG，则使用真实搜索；否则使用模拟搜索
        """
        print(f"\n{'='*60}")
        print(f"[步骤3] 正在搜索信息...")
        print(f"{'='*60}")
        
        all_results = []
        
        for keyword in keywords[:3]:  # 只使用前3个关键词
            print(f"\n正在搜索关键词: {keyword}")
            
            # 根据配置选择搜索方式
            if config.SEARXNG_ENABLED:
                results = self._searxng_search(keyword)
            else:
                results = self._simulate_search(keyword)
            
            all_results.extend(results)
            
            time.sleep(0.5)  # 避免请求过快
        
        print(f"\n共找到 {len(all_results)} 条搜索结果")
        return all_results[:self.max_results]
    
    def _searxng_search(self, keyword: str) -> List[Dict[str, str]]:
        """
        使用SearXNG进行真实搜索
        """
        try:
            # 构建SearXNG API请求
            url = f"{config.SEARXNG_BASE_URL}/search"
            params = {
                'q': keyword,
                'format': 'json',
                'categories': 'general',
                'language': 'zh-CN'
            }
            
            headers = self.headers.copy()
            if config.SEARXNG_API_KEY:
                headers['Authorization'] = f'Bearer {config.SEARXNG_API_KEY}'
            
            response = requests.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 解析SearXNG返回的结果
            for item in data.get('results', [])[:5]:  # 每个关键词取前5个结果
                result = {
                    'title': item.get('title', '无标题'),
                    'url': item.get('url', ''),
                    'content': item.get('content', '') or item.get('snippet', '')
                }
                
                # 如果内容过短，尝试获取完整网页内容
                if len(result['content']) < 100 and result['url']:
                    full_content = self.fetch_content(result['url'])
                    if full_content:
                        result['content'] = full_content
                
                results.append(result)
            
            print(f"  找到 {len(results)} 条真实搜索结果")
            return results
            
        except Exception as e:
            print(f"[警告] SearXNG搜索失败 ({keyword}): {e}")
            print(f"  回退到模拟搜索")
            return self._simulate_search(keyword)
    
    def _simulate_search(self, keyword: str) -> List[Dict[str, str]]:
        """
        模拟搜索（用于演示）
        实际使用时应替换为真实的搜索API调用
        """
        # 这里提供一些模拟数据作为示例
        # 实际应用中，应该调用搜索引擎API或爬取真实网页
        
        if "船舶涂料" in keyword or "销售额" in keyword:
            return [
                {
                    "title": "中国船舶涂料行业市场研究报告 2019-2024",
                    "url": "https://example.com/report1",
                    "content": """根据中国涂料工业协会数据，2019年中国船舶涂料销售额约为85亿元人民币。
                    2020年受疫情影响，销售额下降至约78亿元。2021年随着航运市场复苏，销售额回升至92亿元。
                    2022年达到105亿元，同比增长14%。2023年预计达到115亿元左右。
                    近五年（2019-2023）中国船舶涂料市场保持稳定增长态势，年均复合增长率约为6.3%。
                    主要增长驱动因素包括：造船业复苏、环保涂料需求增加、船舶维修保养市场扩大。"""
                },
                {
                    "title": "2023中国涂料行业年度报告 - 船舶涂料专题",
                    "url": "https://example.com/report2",
                    "content": """中国涂料工业协会发布的年度报告显示：
                    - 2019年船舶涂料销售额：85.3亿元
                    - 2020年船舶涂料销售额：77.8亿元（-8.8%）
                    - 2021年船舶涂料销售额：91.5亿元（+17.6%）
                    - 2022年船舶涂料销售额：104.8亿元（+14.5%）
                    - 2023年船舶涂料销售额：114.2亿元（+9.0%）
                    市场主要参与者包括：海虹老人、佐敦涂料、中远关西等国内外品牌。
                    环保型船舶涂料占比从2019年的45%提升至2023年的68%。"""
                },
                {
                    "title": "航运市场复苏推动船舶涂料需求增长",
                    "url": "https://example.com/news1",
                    "content": """据业内专家分析，近年来中国船舶涂料市场呈现稳定增长趋势。
                    2021-2023年间，随着全球航运市场的复苏和中国造船业的持续发展，
                    船舶涂料需求显著增加。2023年中国船舶涂料销售额突破110亿元大关，
                    预计未来几年仍将保持5-8%的年增长率。
                    高性能防腐涂料和环保型涂料成为市场主流。"""
                },
                {
                    "title": "中国船舶工业行业协会 - 涂料配套数据",
                    "url": "https://example.com/cansi",
                    "content": """根据中国船舶工业行业协会统计：
                    2019-2023年船舶涂料配套情况：
                    2019年：新造船涂料需求约50万吨，销售额85亿元
                    2020年：新造船涂料需求约46万吨，销售额78亿元
                    2021年：新造船涂料需求约54万吨，销售额92亿元
                    2022年：新造船涂料需求约61万吨，销售额105亿元
                    2023年：新造船涂料需求约66万吨，销售额115亿元
                    数据来源：中国船舶工业行业协会、中国涂料工业协会"""
                },
                {
                    "title": "环保政策驱动船舶涂料市场转型升级",
                    "url": "https://example.com/news2",
                    "content": """在IMO 2020等环保法规推动下，船舶涂料行业加速向环保化转型。
                    2019-2023期间，低VOC涂料、无溶剂涂料等环保产品市场份额快速提升。
                    据统计，环保型船舶涂料销售占比从2019年的不足50%提升至2023年的近70%。
                    虽然单价有所提高，但整体市场规模仍保持增长，
                    从2019年的约85亿元增长到2023年的约115亿元。"""
                }
            ]
        
        # 默认返回空结果
        return [
            {
                "title": f"关于 {keyword} 的搜索结果",
                "url": "https://example.com/search",
                "content": f"这是关于 {keyword} 的模拟搜索结果内容。在实际应用中，这里应该是从搜索引擎API获取的真实内容。"
            }
        ]
    
    def fetch_content(self, url: str) -> str:
        """
        获取网页内容
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 获取文本
            text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:5000]  # 限制长度
        
        except Exception as e:
            print(f"[警告] 获取网页内容失败 ({url}): {e}")
            return ""
    
    def create_summary(self, results: List[Dict[str, str]]) -> str:
        """创建搜索结果概要"""
        summary = f"共找到 {len(results)} 条相关信息\n\n"
        
        for i, result in enumerate(results, 1):
            summary += f"{i}. {result['title']}\n"
            summary += f"   内容摘要: {result['content'][:150]}...\n\n"
        
        return summary
