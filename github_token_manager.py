#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Token 管理器
实现多Token轮询机制以提高API调用效率
"""

import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import requests


class GitHubTokenManager:
    """GitHub Token 管理器，支持多Token轮询"""
    
    def __init__(self, tokens: List[str]):
        """
        初始化Token管理器
        
        Args:
            tokens: GitHub Token列表
        """
        if not tokens or not any(tokens):
            raise ValueError("至少需要提供一个有效的GitHub Token")
        
        # 过滤空token
        self.tokens = [t.strip() for t in tokens if t and t.strip()]
        self.current_index = 0
        
        # 每个token的速率限制信息
        self.rate_limits: Dict[str, Dict] = {}
        
        # 初始化所有token的速率信息
        for token in self.tokens:
            self.rate_limits[token] = {
                'remaining': None,  # 剩余请求数
                'reset_time': None,  # 重置时间
                'limit': None,       # 总限制数
                'last_check': None,  # 上次检查时间
                'is_available': True  # 是否可用
            }
        
        print(f"✅ GitHub Token管理器初始化成功，共加载 {len(self.tokens)} 个Token")
    
    def get_current_token(self) -> str:
        """获取当前Token"""
        return self.tokens[self.current_index]
    
    def get_next_token(self) -> str:
        """
        获取下一个可用Token（循环轮询）
        
        策略：
        1. 简单轮询到下一个Token
        2. 不检查配额，不等待
        3. 让调用者决定是否需要等待（只有真正触发API错误时才等待）
        
        Returns:
            下一个Token
        """
        # 简单轮询到下一个Token
        self.current_index = (self.current_index + 1) % len(self.tokens)
        return self.tokens[self.current_index]
    
    def update_rate_limit(self, token: str, response: requests.Response):
        """
        更新Token的速率限制信息
        
        Args:
            token: GitHub Token
            response: API响应对象
        """
        if token not in self.rate_limits:
            return
        
        headers = response.headers
        info = self.rate_limits[token]
        
        # 从响应头中获取速率限制信息
        info['remaining'] = int(headers.get('X-RateLimit-Remaining', 0))
        info['limit'] = int(headers.get('X-RateLimit-Limit', 5000))
        
        reset_timestamp = headers.get('X-RateLimit-Reset')
        if reset_timestamp:
            info['reset_time'] = datetime.fromtimestamp(int(reset_timestamp))
        
        info['last_check'] = datetime.now()
        
        # 如果剩余配额低于10，标记为不可用
        if info['remaining'] < 10:
            info['is_available'] = False
            print(f"⚠️  Token配额不足 (剩余: {info['remaining']}), 切换到下一个Token")
        else:
            info['is_available'] = True
    
    def check_rate_limit(self, token: str) -> Dict:
        """
        主动检查Token的速率限制
        
        Args:
            token: GitHub Token
            
        Returns:
            速率限制信息字典
        """
        url = 'https://api.github.com/rate_limit'
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                search_limit = data.get('resources', {}).get('search', {})
                
                info = self.rate_limits[token]
                info['remaining'] = search_limit.get('remaining', 0)
                info['limit'] = search_limit.get('limit', 30)
                
                reset_timestamp = search_limit.get('reset')
                if reset_timestamp:
                    info['reset_time'] = datetime.fromtimestamp(reset_timestamp)
                
                info['last_check'] = datetime.now()
                info['is_available'] = info['remaining'] > 10
                
                return info
        except Exception as e:
            print(f"❌ 检查速率限制失败: {e}")
        
        return self.rate_limits.get(token, {})
    
    def get_all_rate_limits(self) -> Dict[str, Dict]:
        """
        获取所有Token的速率限制信息
        
        Returns:
            所有Token的速率限制信息
        """
        for token in self.tokens:
            self.check_rate_limit(token)
        
        return self.rate_limits
    
    def print_status(self):
        """打印所有Token的状态"""
        print("\n" + "=" * 80)
        print("GitHub Token 状态")
        print("=" * 80)
        
        for idx, token in enumerate(self.tokens, 1):
            info = self.rate_limits[token]
            masked_token = token[:8] + "..." + token[-4:]
            
            status = "✅ 可用" if info['is_available'] else "❌ 受限"
            remaining = info['remaining'] if info['remaining'] is not None else "未知"
            limit = info['limit'] if info['limit'] is not None else "未知"
            
            print(f"\nToken {idx}: {masked_token}")
            print(f"  状态: {status}")
            print(f"  配额: {remaining}/{limit}")
            
            if info['reset_time']:
                time_until_reset = (info['reset_time'] - datetime.now()).total_seconds()
                if time_until_reset > 0:
                    print(f"  重置: {time_until_reset/60:.1f} 分钟后")
                else:
                    print(f"  重置: 已重置")
        
        print("=" * 80)
    
    def wait_if_needed(self, min_remaining: int = 10):
        """
        如果当前Token配额不足，等待或切换Token
        
        Args:
            min_remaining: 最小剩余配额
        """
        current_token = self.get_current_token()
        info = self.rate_limits[current_token]
        
        if info['remaining'] is not None and info['remaining'] < min_remaining:
            print(f"⚠️  当前Token配额不足 (剩余: {info['remaining']})")
            next_token = self.get_next_token()
            if next_token != current_token:
                print(f"✅ 已切换到新Token")
            else:
                print(f"⏳ 等待Token重置...")
    
    def get_available_token_count(self) -> int:
        """获取可用Token数量"""
        return sum(1 for info in self.rate_limits.values() if info['is_available'])


def load_tokens_from_env() -> List[str]:
    """
    从环境变量加载Token列表
    
    支持格式:
    - GITHUB_TOKEN: 单个token
    - GITHUB_TOKENS: 多个token，用逗号分隔
    
    Returns:
        Token列表
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    tokens = []
    
    # 尝试加载单个token
    single_token = os.getenv('GITHUB_TOKEN', '').strip()
    if single_token:
        tokens.append(single_token)
    
    # 尝试加载多个tokens
    multi_tokens = os.getenv('GITHUB_TOKENS', '').strip()
    if multi_tokens:
        tokens.extend([t.strip() for t in multi_tokens.split(',') if t.strip()])
    
    # 去重
    tokens = list(dict.fromkeys(tokens))  # 保持顺序的去重
    
    return tokens


# 测试代码
if __name__ == '__main__':
    print("测试 GitHub Token 管理器")
    print("=" * 80)
    
    tokens = load_tokens_from_env()
    
    if not tokens:
        print("❌ 未找到GitHub Token")
        print("请在.env文件中配置:")
        print("  GITHUB_TOKEN=your_token_here")
        print("  或")
        print("  GITHUB_TOKENS=token1,token2,token3")
    else:
        manager = GitHubTokenManager(tokens)
        manager.get_all_rate_limits()
        manager.print_status()

