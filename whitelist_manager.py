"""
白名单管理模块 - SecretGuard 密钥泄露监控系统
"""
import os
import yaml
from pathlib import PurePath
from typing import List, Dict


class WhitelistManager:
    """白名单管理器"""
    
    def __init__(self, whitelist_file: str = 'whitelist.yaml'):
        """
        初始化白名单管理器
        
        Args:
            whitelist_file: 白名单配置文件路径
        """
        self.whitelist_file = whitelist_file
        self.repo_patterns = []
        self.file_patterns = []
        self.enabled = False
        
        self._load_whitelist()
    
    def _load_whitelist(self):
        """加载白名单配置"""
        if not os.path.exists(self.whitelist_file):
            print(f"ℹ️  未找到白名单配置文件: {self.whitelist_file}")
            return
        
        try:
            with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                print(f"⚠️  白名单配置文件为空")
                return
            
            # 加载仓库白名单
            self.repo_patterns = config.get('repositories', []) or []
            
            # 加载文件白名单
            self.file_patterns = config.get('files', []) or []
            
            if self.repo_patterns or self.file_patterns:
                self.enabled = True
                print(f"✅ 白名单已加载:")
                if self.repo_patterns:
                    print(f"   - 仓库规则: {len(self.repo_patterns)} 条")
                if self.file_patterns:
                    print(f"   - 文件规则: {len(self.file_patterns)} 条")
            else:
                print(f"ℹ️  白名单配置为空")
                
        except yaml.YAMLError as e:
            print(f"❌ 白名单配置文件格式错误: {e}")
        except Exception as e:
            print(f"❌ 加载白名单失败: {e}")
    
    def is_repo_whitelisted(self, repo_name: str) -> bool:
        """
        检查仓库是否在白名单中
        
        Args:
            repo_name: 仓库全名 (owner/repo)
            
        Returns:
            True: 在白名单中（应该忽略）
            False: 不在白名单中
        """
        if not self.enabled or not self.repo_patterns:
            return False
        
        for pattern in self.repo_patterns:
            # 使用 PurePath.match 支持 ** 递归匹配
            try:
                if PurePath(repo_name).match(pattern):
                    return True
            except:
                # 如果模式无效，跳过
                continue
        
        return False
    
    def is_file_whitelisted(self, file_path: str) -> bool:
        """
        检查文件是否在白名单中
        
        Args:
            file_path: 文件路径
            
        Returns:
            True: 在白名单中（应该忽略）
            False: 不在白名单中
        """
        if not self.enabled or not self.file_patterns:
            return False
        
        for pattern in self.file_patterns:
            # 使用 PurePath.match 支持 ** 递归匹配
            try:
                if PurePath(file_path).match(pattern):
                    return True
            except:
                # 如果模式无效，跳过
                continue
        
        return False
    
    def is_leakage_whitelisted(self, leakage: Dict) -> bool:
        """
        检查泄露是否在白名单中
        
        Args:
            leakage: 泄露信息字典
            
        Returns:
            True: 在白名单中（应该忽略）
            False: 不在白名单中
        """
        if not self.enabled:
            return False
        
        # 检查仓库白名单
        repo_name = leakage.get('repo_name', '')
        if repo_name and self.is_repo_whitelisted(repo_name):
            return True
        
        # 检查文件白名单
        file_path = leakage.get('file_path', '')
        if file_path and self.is_file_whitelisted(file_path):
            return True
        
        return False
    
    def filter_leakages(self, leakages: List[Dict]) -> tuple[List[Dict], int]:
        """
        过滤白名单中的泄露
        
        Args:
            leakages: 泄露列表
            
        Returns:
            (过滤后的泄露列表, 被过滤的数量)
        """
        if not self.enabled or not leakages:
            return leakages, 0
        
        filtered = []
        filtered_count = 0
        
        for leakage in leakages:
            if self.is_leakage_whitelisted(leakage):
                filtered_count += 1
            else:
                filtered.append(leakage)
        
        return filtered, filtered_count
    
    def get_whitelist_summary(self) -> str:
        """
        获取白名单摘要信息
        
        Returns:
            白名单摘要字符串
        """
        if not self.enabled:
            return "未启用白名单"
        
        summary = []
        if self.repo_patterns:
            summary.append(f"仓库: {len(self.repo_patterns)}条")
        if self.file_patterns:
            summary.append(f"文件: {len(self.file_patterns)}条")
        
        return ", ".join(summary) if summary else "白名单为空"

