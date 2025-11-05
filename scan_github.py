#!/usr/bin/env python3
"""
SecretGuard - GitHub 密钥泄露监控系统
用于监控指定密钥清单中的密钥是否泄露到 GitHub 公开仓库
"""
import argparse
import sys
import os
from datetime import datetime
from config import GITHUB_TOKEN, ALL_GITHUB_TOKENS
from scanner import CloudScanner


def print_banner():
    """打印程序横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        SecretGuard - 密钥泄露监控系统                     ║
║        Secret Leakage Monitor for GitHub                 ║
║                                                           ║
║        Version: 2.0.0                                     ║
║        https://github.com/Pa55w0rd/SecretGuard           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def validate_github_token() -> bool:
    """验证GitHub Token是否存在"""
    if not ALL_GITHUB_TOKENS:
        print("❌ 错误: 未找到 GitHub Token")
        print("\n请按以下步骤设置：")
        print("1. 复制 env.example 为 .env")
        print("2. 在 https://github.com/settings/tokens 创建 Personal Access Token")
        print("3. 将 Token 添加到 .env 文件中:")
        print("   GITHUB_TOKEN=your_token_here")
        print("   或配置多个Token（推荐）:")
        print("   GITHUB_TOKENS=token1,token2,token3")
        return False
    
    # 显示加载的Token数量
    token_count = len(ALL_GITHUB_TOKENS)
    if token_count > 1:
        print(f"✅ 已加载 {token_count} 个 GitHub Token")
    else:
        print(f"✅ 已加载 1 个 GitHub Token")
        print(f"💡 提示: 配置多个Token可以提高扫描速度")
    
    return True


def main():
    """主函数"""
    print_banner()
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description='监控您的密钥是否泄露到 GitHub 公开仓库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 监控指定清单中的密钥是否泄露（只搜索代码）
  python scan_github.py --secrets-list my_secrets.txt
  
  # 全面搜索：代码、提交、议题、PR
  python scan_github.py --search-types code commits issues pr
  
  # 搜索代码和PR
  python scan_github.py --search-types code pr
  
  # 使用默认清单文件（secrets_to_monitor.txt）
  python scan_github.py
  
  # 指定输出目录
  python scan_github.py --secrets-list my_secrets.txt --output-dir ./reports
  
注意：
  - 默认只搜索代码文件（API 消耗最少）
  - 搜索多种类型会消耗更多 API 配额
  - 每种类型都会独立计入 30 次/分钟的搜索限制
        """
    )
    
    # 添加参数
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='启用监控模式（默认模式，此参数可省略）'
    )
    
    parser.add_argument(
        '--secrets-list',
        type=str,
        default='secrets_to_monitor.txt',
        help='密钥清单文件路径 (默认: secrets_to_monitor.txt)'
    )
    
    parser.add_argument(
        '--search-types',
        type=str,
        nargs='+',
        choices=['code', 'commits', 'issues', 'pr'],
        default=['code'],
        help='搜索类型 (可选: code commits issues pr)。默认只搜索代码。多种类型会消耗更多API配额'
    )
    
    parser.add_argument(
        '--token',
        type=str,
        help='GitHub Personal Access Token (可选，默认从 .env 读取)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='报告输出目录 (可选，默认: ./scan_reports)'
    )
    
    # 解析参数
    args = parser.parse_args()
    
    # 验证 GitHub Token
    if not validate_github_token():
        sys.exit(1)
    
    # 使用命令行token或配置的tokens
    if args.token:
        tokens = [args.token]
    else:
        tokens = ALL_GITHUB_TOKENS
    
    # 设置输出目录
    if args.output_dir:
        os.environ['OUTPUT_DIR'] = args.output_dir
    
    try:
        # 创建扫描器实例（支持多token轮询）
        scanner = CloudScanner(tokens)
        
        # 执行监控
        report_path = scanner.scan_secrets_list(args.secrets_list, search_types=args.search_types)
        
        print(f"\n✅ 扫描完成！")
        print(f"📄 报告已保存至: {report_path}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断扫描")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 扫描过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
