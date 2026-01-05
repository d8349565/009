"""
报告元数据管理模块
负责报告的元数据生成、存储和检索
"""
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
from pathlib import Path


class ReportMetadata:
    """报告元数据类"""
    
    def __init__(self, 
                 title: str,
                 topic: str,
                 content_summary: str = "",
                 keywords: List[str] = None,
                 data_sources: List[Dict] = None,
                 search_keywords: List[str] = None,
                 related_topics: List[str] = None,
                 report_id: str = None,
                 created_at: str = None,
                 file_path: str = None,
                 tags: List[str] = None):
        """
        初始化报告元数据
        
        Args:
            title: 报告标题
            topic: 主题（用于分类和关联）
            content_summary: 报告摘要（200-500字）
            keywords: 关键词列表
            data_sources: 数据来源列表 [{"url": "", "title": "", "credibility": 8}]
            search_keywords: 搜索时使用的关键词
            related_topics: 相关主题标签
            report_id: 报告唯一ID（自动生成）
            created_at: 创建时间（自动生成）
            file_path: Markdown文件路径
            tags: 主题标签（用于分类和检索）
        """
        self.report_id = report_id or self._generate_id()
        self.title = title
        self.topic = topic
        self.content_summary = content_summary
        self.keywords = keywords or []
        self.data_sources = data_sources or []
        self.search_keywords = search_keywords or []
        self.related_topics = related_topics or []
        self.created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.file_path = file_path
        self.tags = tags or self._extract_tags_from_topic(topic)
    
    def _generate_id(self) -> str:
        """生成唯一报告ID"""
        return str(uuid.uuid4())
    
    def _extract_tags_from_topic(self, topic: str) -> List[str]:
        """从主题中提取标签"""
        # 简单实现：按常见分隔符拆分
        tags = []
        for delimiter in ['、', '，', ',', ' ']:
            if delimiter in topic:
                tags = [t.strip() for t in topic.split(delimiter) if t.strip()]
                break
        
        if not tags:
            tags = [topic]
        
        return tags
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "title": self.title,
            "topic": self.topic,
            "content_summary": self.content_summary,
            "keywords": self.keywords,
            "data_sources": self.data_sources,
            "search_keywords": self.search_keywords,
            "related_topics": self.related_topics,
            "created_at": self.created_at,
            "file_path": self.file_path,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportMetadata':
        """从字典创建"""
        return cls(
            report_id=data.get('report_id'),
            title=data.get('title', ''),
            topic=data.get('topic', ''),
            content_summary=data.get('content_summary', ''),
            keywords=data.get('keywords', []),
            data_sources=data.get('data_sources', []),
            search_keywords=data.get('search_keywords', []),
            related_topics=data.get('related_topics', []),
            created_at=data.get('created_at'),
            file_path=data.get('file_path'),
            tags=data.get('tags', [])
        )
    
    def save_to_file(self, directory: str = "reports"):
        """保存元数据到JSON文件"""
        # 构建JSON文件路径（与Markdown同名，后缀改为.json）
        if self.file_path:
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            json_filename = f"{base_name}.json"
        else:
            json_filename = f"{self.report_id}.json"
        
        json_path = os.path.join(directory, json_filename)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"✓ 元数据已保存: {json_path}")
            return json_path
        except Exception as e:
            print(f"✗ 元数据保存失败: {e}")
            return None


class ReportIndex:
    """报告索引和检索系统"""
    
    def __init__(self, reports_dir: str = "reports"):
        """
        初始化报告索引
        
        Args:
            reports_dir: 报告存储目录
        """
        self.reports_dir = reports_dir
        self.index_file = os.path.join(reports_dir, ".index.json")
        self.index = self.load_index()
    
    def load_index(self) -> Dict[str, Dict]:
        """加载索引文件"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[警告] 索引文件加载失败: {e}，将创建新索引")
                return {}
        return {}
    
    def save_index(self):
        """保存索引文件"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[错误] 索引保存失败: {e}")
    
    def add_report(self, metadata: ReportMetadata):
        """添加报告到索引"""
        self.index[metadata.report_id] = metadata.to_dict()
        self.save_index()
        print(f"✓ 报告已添加到索引: {metadata.title}")
    
    def rebuild_index(self):
        """重建索引（扫描reports目录下所有JSON文件）"""
        print(f"\n开始重建索引...")
        self.index = {}
        count = 0
        
        if not os.path.exists(self.reports_dir):
            print(f"报告目录不存在: {self.reports_dir}")
            return
        
        for filename in os.listdir(self.reports_dir):
            if filename.endswith('.json') and filename != '.index.json':
                json_path = os.path.join(self.reports_dir, filename)
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        metadata = ReportMetadata.from_dict(data)
                        self.index[metadata.report_id] = metadata.to_dict()
                        count += 1
                except Exception as e:
                    print(f"[警告] 无法加载 {filename}: {e}")
        
        self.save_index()
        print(f"✓ 索引重建完成，共 {count} 个报告")
    
    def search(self, 
               keywords: List[str] = None, 
               topic: str = None,
               tags: List[str] = None,
               start_date: str = None,
               end_date: str = None,
               limit: int = 10) -> List[ReportMetadata]:
        """
        搜索报告
        
        Args:
            keywords: 关键词列表（匹配标题、关键词、摘要）
            topic: 主题（模糊匹配）
            tags: 标签列表（至少匹配一个）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 返回结果数量限制
        
        Returns:
            匹配的报告元数据列表（按相关度排序）
        """
        results = []
        
        for report_id, data in self.index.items():
            metadata = ReportMetadata.from_dict(data)
            score = self._calculate_relevance_score(metadata, keywords, topic, tags)
            
            # 时间过滤
            if start_date and metadata.created_at < start_date:
                continue
            if end_date and metadata.created_at > end_date:
                continue
            
            if score > 0:
                results.append((score, metadata))
        
        # 按相关度排序
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [metadata for score, metadata in results[:limit]]
    
    def _calculate_relevance_score(self, 
                                   metadata: ReportMetadata,
                                   keywords: List[str] = None,
                                   topic: str = None,
                                   tags: List[str] = None) -> float:
        """
        计算相关度评分
        
        评分规则：
        - 标题完全匹配关键词：+10分
        - 标题部分匹配：+5分
        - 关键词列表匹配：+3分/个
        - 摘要匹配：+2分/个
        - 主题匹配：+8分
        - 标签匹配：+5分/个
        """
        score = 0.0
        
        # 关键词匹配
        if keywords:
            for keyword in keywords:
                keyword_lower = keyword.lower()
                
                # 标题匹配
                if keyword_lower in metadata.title.lower():
                    if keyword_lower == metadata.title.lower():
                        score += 10
                    else:
                        score += 5
                
                # 关键词列表匹配
                if any(keyword_lower in kw.lower() for kw in metadata.keywords):
                    score += 3
                
                # 摘要匹配
                if keyword_lower in metadata.content_summary.lower():
                    score += 2
                
                # 搜索关键词匹配
                if any(keyword_lower in sk.lower() for sk in metadata.search_keywords):
                    score += 2
        
        # 主题匹配
        if topic and topic.lower() in metadata.topic.lower():
            score += 8
        
        # 标签匹配
        if tags:
            for tag in tags:
                if any(tag.lower() in t.lower() for t in metadata.tags):
                    score += 5
        
        return score
    
    def find_related_reports(self, 
                           reference_keywords: List[str] = None,
                           reference_topic: str = None,
                           reference_tags: List[str] = None,
                           min_score: float = 5.0,
                           limit: int = 10) -> List[tuple]:
        """
        查找相关报告（用于综合报告功能）
        
        与search()的区别：
        - search(): 用户主动搜索，需要精确匹配
        - find_related_reports(): AI自动发现相关报告，更宽泛的相似度匹配
        
        Args:
            reference_keywords: 参考关键词列表
            reference_topic: 参考主题
            reference_tags: 参考标签列表
            min_score: 最低相关度分数（默认5.0）
            limit: 返回数量限制
            
        Returns:
            [(score, metadata), ...] 按相关度降序排序
        """
        results = []
        
        for report_id, metadata_dict in self.index.items():
            metadata = ReportMetadata.from_dict(metadata_dict)
            score = self._calculate_relevance_score(
                metadata,
                keywords=reference_keywords,
                topic=reference_topic,
                tags=reference_tags
            )
            
            if score >= min_score:
                results.append((score, metadata))
        
        # 按相关度降序排序
        results.sort(key=lambda x: x[0], reverse=True)
        
        return results[:limit]
    
    def get_report_with_content(self, report_id: str) -> Dict[str, Any]:
        """
        获取报告的完整信息（元数据 + 内容）
        
        Args:
            report_id: 报告ID
            
        Returns:
            {
                'metadata': ReportMetadata对象,
                'content': 报告内容（Markdown字符串）
            }
        """
        metadata = self.get_report_by_id(report_id)
        if not metadata:
            return None
        
        content = self.get_report_content(report_id)
        if not content:
            return None
        
        return {
            'metadata': metadata,
            'content': content
        }
    
    def get_report_by_id(self, report_id: str) -> Optional[ReportMetadata]:
        """根据ID获取报告元数据"""
        data = self.index.get(report_id)
        if data:
            return ReportMetadata.from_dict(data)
        return None
    
    def get_report_content(self, report_id: str) -> Optional[str]:
        """读取报告Markdown内容"""
        metadata = self.get_report_by_id(report_id)
        if not metadata or not metadata.file_path:
            return None
        
        file_path = metadata.file_path
        # 如果路径不是绝对路径，且不以reports/开头，则添加reports目录
        if not os.path.isabs(file_path):
            # 检查路径是否已包含reports目录
            if not file_path.startswith('reports'):
                file_path = os.path.join(self.reports_dir, file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"[错误] 读取报告失败: {e}")
            return None
    
    def list_all_topics(self) -> List[str]:
        """列出所有主题"""
        topics = set()
        for data in self.index.values():
            topics.add(data.get('topic', ''))
        return sorted(list(topics))
    
    def list_all_tags(self) -> List[str]:
        """列出所有标签"""
        tags = set()
        for data in self.index.values():
            tags.update(data.get('tags', []))
        return sorted(list(tags))
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_reports = len(self.index)
        topics = self.list_all_topics()
        tags = self.list_all_tags()
        
        # 按月份统计
        monthly_stats = {}
        for data in self.index.values():
            created_at = data.get('created_at', '')
            month = created_at[:7] if len(created_at) >= 7 else 'unknown'
            monthly_stats[month] = monthly_stats.get(month, 0) + 1
        
        return {
            'total_reports': total_reports,
            'total_topics': len(topics),
            'total_tags': len(tags),
            'topics': topics,
            'tags': tags,
            'monthly_distribution': monthly_stats
        }


def extract_summary_from_markdown(content: str, max_length: int = 500) -> str:
    """从Markdown内容中提取摘要"""
    lines = content.split('\n')
    summary_lines = []
    char_count = 0
    
    # 跳过标题和元数据部分
    start_collecting = False
    for line in lines:
        line = line.strip()
        
        # 跳过标题
        if line.startswith('#'):
            if '执行摘要' in line or '摘要' in line or '概述' in line:
                start_collecting = True
            continue
        
        # 跳过空行
        if not line:
            continue
        
        # 跳过元数据分隔符
        if line.startswith('---'):
            continue
        
        # 开始收集内容
        if start_collecting or (not summary_lines and len(line) > 20):
            summary_lines.append(line)
            char_count += len(line)
            
            if char_count >= max_length:
                break
    
    # 如果没有找到摘要部分，取前面的内容
    if not summary_lines:
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('---'):
                summary_lines.append(line)
                char_count += len(line)
                if char_count >= max_length:
                    break
    
    summary = ' '.join(summary_lines)
    return summary[:max_length] + '...' if len(summary) > max_length else summary


if __name__ == "__main__":
    # 测试代码
    print("=== 报告元数据系统测试 ===\n")
    
    # 创建测试元数据
    metadata = ReportMetadata(
        title="2025年中国汽车行业研究报告",
        topic="汽车行业",
        content_summary="本报告分析了2025年中国汽车行业的发展趋势...",
        keywords=["汽车", "销量", "新能源", "2025"],
        tags=["汽车行业", "市场分析", "2025年"]
    )
    
    print("1. 元数据对象创建成功")
    print(f"   - ID: {metadata.report_id}")
    print(f"   - 标题: {metadata.title}")
    print(f"   - 标签: {metadata.tags}")
    
    # 测试索引系统
    index = ReportIndex()
    print(f"\n2. 索引系统初始化成功")
    print(f"   - 当前报告数: {len(index.index)}")
    
    # 如果有报告目录，尝试重建索引
    if os.path.exists("reports"):
        index.rebuild_index()
        stats = index.get_statistics()
        print(f"\n3. 索引统计:")
        print(f"   - 总报告数: {stats['total_reports']}")
        print(f"   - 主题数: {stats['total_topics']}")
        print(f"   - 标签数: {stats['total_tags']}")
        
        if stats['tags']:
            print(f"   - 标签列表: {', '.join(stats['tags'][:5])}")
    
    print("\n✓ 测试完成")
