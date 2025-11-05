"""
泄露监控模块
用于监控指定密钥清单是否泄露到GitHub
"""
import time
from datetime import datetime
from typing import List, Dict, Optional
from github_scanner import GitHubScanner
from secrets_list import SecretsListLoader, SecretItem, get_type_display_name
from config import SEARCH_DELAY_PER_SECRET, MAX_RESULTS_PER_SECRET


class LeakageMonitor:
    """密钥泄露监控器"""
    
    def __init__(self, github_scanner: GitHubScanner, secrets_file: str = None, 
                 search_types: List[str] = None, token_manager=None, dingtalk_notifier=None,
                 whitelist_manager=None):
        """
        初始化监控器
        
        Args:
            github_scanner: GitHubScanner 实例
            secrets_file: 密钥清单文件路径（可选）
            search_types: 搜索类型列表，可选: 'code', 'commits', 'issues' (可选)
            token_manager: GitHubTokenManager 实例（可选，用于多Token轮询）
            dingtalk_notifier: DingTalkNotifier 实例（可选，用于发送钉钉通知）
            whitelist_manager: WhitelistManager 实例（可选，用于过滤白名单）
        """
        self.github_scanner = github_scanner
        self.token_manager = token_manager
        self.dingtalk_notifier = dingtalk_notifier
        self.whitelist_manager = whitelist_manager
        self.secrets_loader = SecretsListLoader()
        self.secrets: List[SecretItem] = []
        self.search_delay = SEARCH_DELAY_PER_SECRET if not token_manager else 0.5  # 多Token时缩短延迟
        self.max_results = MAX_RESULTS_PER_SECRET
        self.search_types = search_types or ['code']  # 默认只搜索代码
        self.api_call_count = 0  # API调用计数
        
        if secrets_file:
            self.load_secrets(secrets_file)
    
    def load_secrets(self, secrets_file: str):
        """
        加载密钥清单
        
        Args:
            secrets_file: 密钥清单文件路径
        """
        print(f"📂 加载密钥清单: {secrets_file}")
        self.secrets = self.secrets_loader.load_from_file(secrets_file)
        self.secrets_loader.print_summary()
    
    def scan_all_secrets(self) -> List[Dict]:
        """
        扫描清单中的所有密钥
        
        Returns:
            泄露信息列表
        """
        if not self.secrets:
            print("❌ 密钥清单为空，请先加载密钥清单")
            return []
        
        print(f"\n🔍 开始监控 {len(self.secrets)} 个密钥...")
        print("=" * 60)
        
        all_leakages = []
        total_count = len(self.secrets)
        found_count = 0
        
        for idx, secret_item in enumerate(self.secrets, 1):
            print(f"\n[{idx}/{total_count}] 检查密钥: {get_type_display_name(secret_item.secret_type)}")
            print(f"  密钥值: {secret_item.mask_value()}")
            if secret_item.note:
                print(f"  备注: {secret_item.note}")
            
            # 搜索密钥泄露
            leakages = self.scan_single_secret(secret_item)
            
            if leakages:
                found_count += 1
                all_leakages.extend(leakages)
            
            # 延迟以避免API速率限制（最后一个不需要延迟）
            if idx < total_count:
                time.sleep(self.search_delay)
        
        print("\n" + "=" * 60)
        print(f"✅ 扫描完成！")
        print(f"   总密钥数: {total_count}")
        print(f"   发现泄露: {found_count} 个密钥")
        print(f"   泄露位置: {len(all_leakages)} 处")
        
        return all_leakages
    
    def scan_single_secret(self, secret_item: SecretItem) -> List[Dict]:
        """
        扫描单个密钥
        
        Args:
            secret_item: 密钥项
            
        Returns:
            泄露信息列表
        """
        # 主动检查搜索配额并切换Token（如果配置了token_manager）
        if self.token_manager:
            try:
                rate_limit = self.github_scanner.github.get_rate_limit()
                search_limit = rate_limit.search
                
                if search_limit.remaining <= 2:
                    print(f"  ⚠️  当前Token配额不足 (剩余: {search_limit.remaining})")
                    # 切换Token
                    self.github_scanner.switch_token_if_needed()
            except Exception as e:
                pass  # 如果检查失败，继续执行
        else:
            # 没有token_manager，使用原来的等待逻辑
            try:
                rate_limit = self.github_scanner.github.get_rate_limit()
                search_limit = rate_limit.search
                
                if search_limit.remaining <= 1:
                    reset_seconds = (search_limit.reset - datetime.now()).total_seconds()
                    if reset_seconds > 0:
                        print(f"  ⏸️  搜索配额已用完 ({search_limit.remaining}/{search_limit.limit})")
                        print(f"     主动等待 {int(reset_seconds + 5)} 秒后继续...")
                        time.sleep(reset_seconds + 5)
            except Exception:
                pass
        
        leakages = self.github_scanner.search_secret_leakage(
            secret_item.secret_value,
            max_results=self.max_results,
            search_types=self.search_types
        )
        
        # 添加密钥信息到每个泄露记录
        for leakage in leakages:
            leakage['secret_type'] = secret_item.secret_type
            leakage['secret_type_display'] = get_type_display_name(secret_item.secret_type)
            leakage['secret_value'] = secret_item.secret_value
            leakage['secret_masked'] = secret_item.mask_value()
            leakage['secret_note'] = secret_item.note
            leakage['scan_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 检查白名单，只有不在白名单的泄露才发送钉钉告警
            if self.dingtalk_notifier:
                # 如果配置了白名单，先检查
                if self.whitelist_manager and self.whitelist_manager.enabled:
                    if not self.whitelist_manager.is_leakage_whitelisted(leakage):
                        self.dingtalk_notifier.send_leakage_alert(leakage)
                else:
                    # 没有白名单或白名单未启用，直接发送
                    self.dingtalk_notifier.send_leakage_alert(leakage)
        
        return leakages
    
    def get_statistics(self, leakages: List[Dict]) -> Dict:
        """
        获取泄露统计信息
        
        Args:
            leakages: 泄露列表
            
        Returns:
            统计信息字典
        """
        if not leakages:
            return {
                'total_secrets': len(self.secrets),
                'leaked_secrets': 0,
                'total_leakages': 0,
                'leakage_rate': 0.0,
                'by_type': {},
                'by_repo': {},
                'unique_repos': 0
            }
        
        # 统计泄露的密钥数（去重）
        leaked_secrets = set()
        by_type = {}
        by_repo = {}
        
        for leakage in leakages:
            leaked_secrets.add(leakage['secret_value'])
            
            # 按类型统计
            secret_type = leakage['secret_type']
            if secret_type not in by_type:
                by_type[secret_type] = {
                    'count': 0,
                    'display_name': leakage['secret_type_display']
                }
            by_type[secret_type]['count'] += 1
            
            # 按仓库统计
            repo_name = leakage['repo_name']
            if repo_name not in by_repo:
                by_repo[repo_name] = {
                    'count': 0,
                    'url': leakage['repo_url']
                }
            by_repo[repo_name]['count'] += 1
        
        leaked_count = len(leaked_secrets)
        total_secrets = len(self.secrets)
        leakage_rate = (leaked_count / total_secrets * 100) if total_secrets > 0 else 0
        
        return {
            'total_secrets': total_secrets,
            'leaked_secrets': leaked_count,
            'total_leakages': len(leakages),
            'leakage_rate': leakage_rate,
            'by_type': by_type,
            'by_repo': by_repo,
            'unique_repos': len(by_repo)
        }
    
    def group_leakages_by_secret(self, leakages: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按密钥分组泄露信息
        
        Args:
            leakages: 泄露列表
            
        Returns:
            分组后的字典 {密钥值: [泄露位置列表]}
        """
        grouped = {}
        for leakage in leakages:
            secret_value = leakage['secret_value']
            if secret_value not in grouped:
                grouped[secret_value] = []
            grouped[secret_value].append(leakage)
        return grouped
    
    def print_summary(self, leakages: List[Dict]):
        """
        打印扫描摘要
        
        Args:
            leakages: 泄露列表
        """
        stats = self.get_statistics(leakages)
        
        print("\n" + "=" * 60)
        print("📊 扫描摘要")
        print("=" * 60)
        print(f"总密钥数量: {stats['total_secrets']}")
        print(f"泄露密钥数: {stats['leaked_secrets']}")
        print(f"泄露位置数: {stats['total_leakages']}")
        print(f"泄露率: {stats['leakage_rate']:.1f}%")
        print(f"涉及仓库: {stats['unique_repos']}")
        
        if stats['by_type']:
            print(f"\n按类型统计:")
            for secret_type, info in sorted(stats['by_type'].items()):
                print(f"  - {info['display_name']}: {info['count']} 处")
        
        if stats['by_repo']:
            print(f"\n泄露最多的仓库 (前5):")
            sorted_repos = sorted(stats['by_repo'].items(), key=lambda x: x[1]['count'], reverse=True)
            for repo_name, info in sorted_repos[:5]:
                print(f"  - {repo_name}: {info['count']} 处")
        
        print("=" * 60)


class LeakageResult:
    """泄露结果封装类"""
    
    def __init__(self, leakages: List[Dict], statistics: Dict):
        """
        初始化泄露结果
        
        Args:
            leakages: 泄露列表
            statistics: 统计信息
        """
        self.leakages = leakages
        self.statistics = statistics
        self.scan_time = datetime.now()
    
    def has_leakages(self) -> bool:
        """是否发现泄露"""
        return len(self.leakages) > 0
    
    def get_critical_leakages(self) -> List[Dict]:
        """
        获取高危泄露（star数高的公开仓库）
        
        Returns:
            高危泄露列表
        """
        return [l for l in self.leakages if l.get('repo_stars', 0) > 10]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'leakages': self.leakages,
            'statistics': self.statistics,
            'scan_time': self.scan_time.strftime('%Y-%m-%d %H:%M:%S')
        }

