"""
报告检索命令行工具
用于搜索、查看和管理历史报告
"""
from report_metadata import ReportIndex, ReportMetadata
import sys
import os


def print_separator(char='=', length=60):
    """打印分隔线"""
    print(char * length)


def print_report_summary(metadata: ReportMetadata, index: int = None):
    """打印报告摘要"""
    prefix = f"[{index}] " if index is not None else ""
    print(f"\n{prefix}📄 {metadata.title}")
    print(f"   🏷️  主题: {metadata.topic}")
    print(f"   🔖 标签: {', '.join(metadata.tags[:3])}")
    print(f"   📅 创建: {metadata.created_at}")
    print(f"   🔑 关键词: {', '.join(metadata.keywords[:5])}")
    if metadata.content_summary:
        summary = metadata.content_summary[:150] + '...' if len(metadata.content_summary) > 150 else metadata.content_summary
        print(f"   📝 摘要: {summary}")
    print(f"   📂 文件: {metadata.file_path}")


def search_reports(index: ReportIndex):
    """搜索报告"""
    print_separator()
    print("🔍 报告搜索")
    print_separator()
    
    print("\n请输入搜索条件（留空跳过）:")
    keywords_input = input("关键词（多个用空格分隔）: ").strip()
    topic_input = input("主题: ").strip()
    tags_input = input("标签（多个用空格分隔）: ").strip()
    
    # 解析输入
    keywords = keywords_input.split() if keywords_input else None
    topic = topic_input if topic_input else None
    tags = tags_input.split() if tags_input else None
    
    # 执行搜索
    results = index.search(keywords=keywords, topic=topic, tags=tags, limit=20)
    
    if not results:
        print("\n❌ 未找到匹配的报告")
        return
    
    print(f"\n✅ 找到 {len(results)} 个匹配的报告:")
    print_separator('-')
    
    for i, metadata in enumerate(results, 1):
        print_report_summary(metadata, i)
    
    # 询问是否查看详情
    print_separator('-')
    choice = input("\n输入报告编号查看详情（留空返回）: ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            view_report_detail(index, results[idx])


def view_report_detail(index: ReportIndex, metadata: ReportMetadata):
    """查看报告详情"""
    print_separator()
    print(f"📄 报告详情: {metadata.title}")
    print_separator()
    
    print(f"\n基本信息:")
    print(f"  主题: {metadata.topic}")
    print(f"  标签: {', '.join(metadata.tags)}")
    print(f"  创建时间: {metadata.created_at}")
    print(f"  报告ID: {metadata.report_id}")
    
    print(f"\n关键词:")
    print(f"  {', '.join(metadata.keywords)}")
    
    if metadata.search_keywords:
        print(f"\n搜索关键词:")
        print(f"  {', '.join(metadata.search_keywords)}")
    
    if metadata.content_summary:
        print(f"\n内容摘要:")
        print(f"  {metadata.content_summary}")
    
    if metadata.data_sources:
        print(f"\n数据来源 ({len(metadata.data_sources)}个):")
        for i, source in enumerate(metadata.data_sources[:5], 1):
            print(f"  {i}. {source.get('title', '无标题')}")
            print(f"     URL: {source.get('url', '')}")
            print(f"     可信度: {source.get('credibility', 'N/A')}/10")
    
    print(f"\n文件路径: {metadata.file_path}")
    
    # 询问是否打开报告
    choice = input("\n是否打开报告文件？(y/n): ").strip().lower()
    if choice == 'y':
        open_report_file(metadata.file_path)


def open_report_file(filepath: str):
    """打开报告文件"""
    try:
        if os.name == 'nt':  # Windows
            os.startfile(filepath)
            print("✓ 已在默认程序中打开报告")
        else:  # macOS/Linux
            import subprocess
            subprocess.run(['xdg-open', filepath])
            print("✓ 已在默认程序中打开报告")
    except Exception as e:
        print(f"✗ 打开失败: {e}")


def list_all_topics(index: ReportIndex):
    """列出所有主题"""
    print_separator()
    print("📚 所有主题")
    print_separator()
    
    topics = index.list_all_topics()
    if not topics:
        print("\n暂无报告")
        return
    
    for i, topic in enumerate(topics, 1):
        # 统计该主题下的报告数
        count = sum(1 for data in index.index.values() if data.get('topic') == topic)
        print(f"{i:2d}. {topic} ({count}个报告)")


def list_all_tags(index: ReportIndex):
    """列出所有标签"""
    print_separator()
    print("🏷️  所有标签")
    print_separator()
    
    tags = index.list_all_tags()
    if not tags:
        print("\n暂无标签")
        return
    
    print(f"\n共 {len(tags)} 个标签:")
    for i, tag in enumerate(tags, 1):
        # 统计该标签的报告数
        count = sum(1 for data in index.index.values() if tag in data.get('tags', []))
        print(f"  {tag} ({count})")


def show_statistics(index: ReportIndex):
    """显示统计信息"""
    print_separator()
    print("📊 报告库统计")
    print_separator()
    
    stats = index.get_statistics()
    
    print(f"\n总报告数: {stats['total_reports']}")
    print(f"主题数: {stats['total_topics']}")
    print(f"标签数: {stats['total_tags']}")
    
    if stats['monthly_distribution']:
        print(f"\n月度分布:")
        for month, count in sorted(stats['monthly_distribution'].items(), reverse=True)[:6]:
            print(f"  {month}: {count}个报告")


def rebuild_index(index: ReportIndex):
    """重建索引"""
    print_separator()
    print("🔄 重建索引")
    print_separator()
    
    confirm = input("\n确认重建索引？这将扫描reports目录下所有JSON文件 (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    index.rebuild_index()


def main_menu():
    """主菜单"""
    index = ReportIndex()
    
    while True:
        print("\n")
        print_separator()
        print("📚 报告检索系统")
        print_separator()
        print(f"当前报告数: {len(index.index)}")
        print_separator()
        print("\n请选择操作:")
        print("  1. 搜索报告")
        print("  2. 查看所有主题")
        print("  3. 查看所有标签")
        print("  4. 统计信息")
        print("  5. 重建索引")
        print("  0. 退出")
        print_separator()
        
        choice = input("\n请输入选项: ").strip()
        
        if choice == '1':
            search_reports(index)
        elif choice == '2':
            list_all_topics(index)
        elif choice == '3':
            list_all_tags(index)
        elif choice == '4':
            show_statistics(index)
        elif choice == '5':
            rebuild_index(index)
        elif choice == '0':
            print("\n再见！👋")
            break
        else:
            print("\n❌ 无效选项，请重新输入")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n程序已终止")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
