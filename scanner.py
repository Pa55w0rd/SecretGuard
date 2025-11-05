"""
主扫描器模块 - 密钥泄露监控
"""
import time
from datetime import datetime
from typing import List, Dict, Optional, Union
from github_scanner import GitHubScanner
from html_report_generator import HTMLReportGenerator
from leakage_monitor import LeakageMonitor
from github_token_manager import GitHubTokenManager
from dingtalk_notifier import DingTalkNotifier
from whitelist_manager import WhitelistManager


class CloudScanner:
    """密钥泄露监控扫描器"""
    
    def __init__(self, github_token: Union[str, List[str]], skip_scanned: bool = True, timeout_minutes: int = 50):
        """
        初始化扫描器
        
        Args:
            github_token: GitHub Personal Access Token 或 Token列表
            skip_scanned: 已弃用，保留以兼容旧代码
            timeout_minutes: 扫描超时时间（分钟），默认50分钟
        """
        # 支持单token或多token
        if isinstance(github_token, str):
            tokens = [github_token]
        else:
            tokens = github_token
        
        # 初始化Token管理器（如果有多个token）
        if len(tokens) > 1:
            self.token_manager = GitHubTokenManager(tokens)
            print(f"✅ 使用多Token轮询模式（{len(tokens)}个Token）")
            current_token = self.token_manager.get_current_token()
        else:
            self.token_manager = None
            current_token = tokens[0]
        
        self.github_scanner = GitHubScanner(current_token, token_manager=self.token_manager)
        self.report_generator = HTMLReportGenerator()
        self.dingtalk_notifier = DingTalkNotifier()
        self.whitelist_manager = WhitelistManager()
        self.timeout_seconds = timeout_minutes * 60
        self.scan_start_time = None
        self.tokens = tokens
    
    def scan_secrets_list(self, secrets_file: str, search_types: List[str] = None) -> str:
        """
        监控模式：扫描指定密钥清单中的密钥是否泄露
        
        Args:
            secrets_file: 密钥清单文件路径
            search_types: 搜索类型列表 (可选: code, commits, issues)
            
        Returns:
            报告文件路径
        """
        print(f"🔒 密钥泄露监控模式")
        print(f"=" * 60)
        
        # 显示搜索类型
        if search_types:
            type_names = {'code': 'Code', 'commits': 'Commits', 'issues': 'Issues', 'pr': 'Pull Requests'}
            search_display = ', '.join([type_names.get(t, t) for t in search_types])
            print(f"🔍 搜索范围: {search_display}")
        
        # 显示 API 速率限制状态
        self.github_scanner.display_rate_limit()
        print()
        
        scan_start_time = datetime.now()
        
        try:
            # 创建监控器并加载密钥清单
            monitor = LeakageMonitor(
                self.github_scanner, 
                secrets_file, 
                search_types=search_types,
                token_manager=self.token_manager,  # 传递token管理器
                dingtalk_notifier=self.dingtalk_notifier,  # 传递钉钉通知器
                whitelist_manager=self.whitelist_manager  # 传递白名单管理器
            )
            
            # 扫描所有密钥
            leakages = monitor.scan_all_secrets()
            
            # 应用白名单过滤
            if self.whitelist_manager.enabled:
                filtered_leakages, filtered_count = self.whitelist_manager.filter_leakages(leakages)
                if filtered_count > 0:
                    print(f"\n🔒 白名单过滤: 已过滤 {filtered_count} 处泄露")
                leakages = filtered_leakages
            
            # 打印摘要
            monitor.print_summary(leakages)
            
            # 生成报告
            print(f"\n📝 生成报告...")
            report_path = self.report_generator.generate_monitor_report(
                leakages,
                monitor.get_statistics(leakages),
                scan_start_time,
                secrets_file
            )
            
            # 打印最终摘要
            summary = self.report_generator.generate_monitor_summary(
                report_path,
                len(leakages),
                monitor.get_statistics(leakages)
            )
            print(summary)
            
            # 显示最终 API 使用情况
            print()
            self.github_scanner.display_rate_limit()
            
            return report_path
            
        except FileNotFoundError as e:
            print(f"\n❌ 错误: {e}")
            print(f"\n💡 提示:")
            print(f"   1. 确保密钥清单文件存在")
            print(f"   2. 可以复制 secrets_to_monitor.example.txt 为起点")
            raise
        except Exception as e:
            print(f"\n❌ 扫描过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            raise
