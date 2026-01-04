"""
性能计时工具
"""
import time
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class PerformanceTimer:
    """性能计时器 - 用于跟踪和分析各个环节的耗时"""
    
    def __init__(self):
        """初始化计时器"""
        self.timers: Dict[str, List[Dict]] = defaultdict(list)
        self.stack: List[tuple] = []  # 用于嵌套计时
        self.total_start_time = None
        self.total_end_time = None
        
    def start_total(self):
        """开始总计时"""
        self.total_start_time = time.time()
        
    def end_total(self):
        """结束总计时"""
        self.total_end_time = time.time()
    
    def get_total_duration(self) -> float:
        """
        获取总耗时（秒）
        
        Returns:
            总耗时，如果还未结束则返回0
        """
        if self.total_start_time is not None and self.total_end_time is not None:
            return self.total_end_time - self.total_start_time
        return 0
        
    def start(self, name: str, description: str = ""):
        """
        开始计时一个环节
        
        Args:
            name: 环节名称（唯一标识）
            description: 环节描述
        """
        start_time = time.time()
        self.stack.append((name, start_time, description))
        
    def end(self, name: str, extra_info: Dict = None):
        """
        结束计时一个环节
        
        Args:
            name: 环节名称（必须与start时相同）
            extra_info: 额外信息（如处理的数据量等）
        """
        end_time = time.time()
        
        # 从栈中找到匹配的开始时间
        if not self.stack:
            print(f"[警告] 计时器栈为空，无法结束 '{name}'")
            return
            
        # 找到对应的开始记录
        found = False
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == name:
                start_name, start_time, description = self.stack.pop(i)
                duration = end_time - start_time
                
                # 记录计时数据
                self.timers[name].append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'description': description,
                    'extra_info': extra_info or {}
                })
                
                found = True
                break
        
        if not found:
            print(f"[警告] 未找到 '{name}' 的开始计时记录")
    
    def get_summary(self) -> Dict:
        """
        获取性能统计摘要
        
        Returns:
            包含各环节统计信息的字典
        """
        summary = {}
        total_time = 0
        
        if self.total_start_time and self.total_end_time:
            total_time = self.total_end_time - self.total_start_time
        
        for name, records in self.timers.items():
            total_duration = sum(r['duration'] for r in records)
            avg_duration = total_duration / len(records) if records else 0
            count = len(records)
            
            summary[name] = {
                'count': count,
                'total_duration': total_duration,
                'avg_duration': avg_duration,
                'percentage': (total_duration / total_time * 100) if total_time > 0 else 0,
                'records': records
            }
        
        return {
            'total_time': total_time,
            'components': summary
        }
    
    def print_report(self, detailed: bool = False):
        """
        打印性能分析报告
        
        Args:
            detailed: 是否打印详细信息
        """
        summary = self.get_summary()
        total_time = summary['total_time']
        
        print("\n" + "="*80)
        print("性能分析报告")
        print("="*80)
        
        if total_time > 0:
            print(f"\n总耗时: {self._format_duration(total_time)}")
            print(f"开始时间: {datetime.fromtimestamp(self.total_start_time).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"结束时间: {datetime.fromtimestamp(self.total_end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "-"*80)
        print(f"{'环节名称':<30} {'次数':<8} {'总耗时':<15} {'平均耗时':<15} {'占比':<10}")
        print("-"*80)
        
        # 按总耗时排序
        sorted_components = sorted(
            summary['components'].items(),
            key=lambda x: x[1]['total_duration'],
            reverse=True
        )
        
        for name, stats in sorted_components:
            count = stats['count']
            total_dur = stats['total_duration']
            avg_dur = stats['avg_duration']
            percentage = stats['percentage']
            
            print(f"{name:<30} {count:<8} {self._format_duration(total_dur):<15} "
                  f"{self._format_duration(avg_dur):<15} {percentage:>6.2f}%")
        
        print("-"*80)
        
        # 详细信息
        if detailed:
            print("\n详细信息:")
            print("="*80)
            
            for name, stats in sorted_components:
                print(f"\n【{name}】")
                print(f"  调用次数: {stats['count']}")
                print(f"  总耗时: {self._format_duration(stats['total_duration'])}")
                print(f"  平均耗时: {self._format_duration(stats['avg_duration'])}")
                
                if stats['records']:
                    print(f"  详细记录:")
                    for i, record in enumerate(stats['records'], 1):
                        desc = record.get('description', '')
                        duration = record['duration']
                        extra = record.get('extra_info', {})
                        
                        info_parts = [f"耗时: {self._format_duration(duration)}"]
                        if desc:
                            info_parts.append(f"描述: {desc}")
                        if extra:
                            extra_str = ", ".join(f"{k}={v}" for k, v in extra.items())
                            info_parts.append(f"信息: {extra_str}")
                        
                        print(f"    {i}. {' | '.join(info_parts)}")
        
        print("="*80 + "\n")
        
        # 性能建议
        self._print_suggestions(summary)
    
    def _print_suggestions(self, summary: Dict):
        """打印性能优化建议"""
        print("\n💡 性能优化建议:")
        print("-"*80)
        
        components = summary['components']
        total_time = summary['total_time']
        
        if not components:
            print("  暂无数据")
            return
        
        # 找出最耗时的环节
        slowest = max(components.items(), key=lambda x: x[1]['total_duration'])
        slowest_name, slowest_stats = slowest
        
        if slowest_stats['percentage'] > 50:
            print(f"  ⚠️  '{slowest_name}' 占用了 {slowest_stats['percentage']:.1f}% 的时间，是主要瓶颈")
            
            if 'LLM调用' in slowest_name or 'API' in slowest_name:
                print(f"     建议: 考虑使用更快的模型或减少API调用次数")
            elif '搜索' in slowest_name:
                print(f"     建议: 减少搜索关键词数量或优化搜索策略")
            elif '评估' in slowest_name or '分析' in slowest_name:
                print(f"     建议: 简化评估逻辑或使用缓存")
        
        # 检查是否有重复调用
        for name, stats in components.items():
            if stats['count'] > 5:
                print(f"  ℹ️  '{name}' 被调用了 {stats['count']} 次")
                print(f"     建议: 检查是否可以批量处理或使用缓存")
        
        # 检查API调用
        api_calls = [name for name in components.keys() if 'LLM' in name or 'API' in name]
        if api_calls:
            total_api_time = sum(components[name]['total_duration'] for name in api_calls)
            api_percentage = (total_api_time / total_time * 100) if total_time > 0 else 0
            
            if api_percentage > 60:
                print(f"  ⚠️  API调用总计占用 {api_percentage:.1f}% 的时间")
                print(f"     建议: 这是主要瓶颈，考虑:")
                print(f"       - 使用更快的API端点或模型")
                print(f"       - 并行化API调用")
                print(f"       - 减少prompt长度")
                print(f"       - 使用结果缓存")
        
        print("-"*80)
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 1:
            return f"{seconds*1000:.2f}ms"
        elif seconds < 60:
            return f"{seconds:.2f}s"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.2f}s"
    
    def export_to_dict(self) -> Dict:
        """导出为字典格式，可用于保存到文件"""
        return {
            'total_start_time': self.total_start_time,
            'total_end_time': self.total_end_time,
            'summary': self.get_summary(),
            'export_time': datetime.now().isoformat()
        }


# 全局计时器实例（可选）
_global_timer = None


def get_global_timer() -> PerformanceTimer:
    """获取全局计时器实例"""
    global _global_timer
    if _global_timer is None:
        _global_timer = PerformanceTimer()
    return _global_timer


def reset_global_timer():
    """重置全局计时器"""
    global _global_timer
    _global_timer = PerformanceTimer()
