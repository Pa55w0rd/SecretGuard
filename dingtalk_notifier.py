#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉消息通知模块
"""
import os
import json
import requests
from typing import Dict, List
from datetime import datetime


class DingTalkNotifier:
    """钉钉机器人通知器"""
    
    def __init__(self, webhook_url: str = None):
        """
        初始化钉钉通知器
        
        Args:
            webhook_url: 钉钉机器人webhook地址
        """
        self.webhook_url = webhook_url or os.getenv('DINGTALK_WEBHOOK', '')
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            print("⚠️  未配置钉钉Webhook，通知功能已禁用")
    
    def send_leakage_alert(self, leakage: Dict) -> bool:
        """
        发送密钥泄露告警
        
        Args:
            leakage: 泄露信息字典
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            return False
        
        try:
            # 构建消息内容
            secret_type = leakage.get('secret_type_display', '未知类型')
            secret_masked = leakage.get('secret_masked', '')
            secret_note = leakage.get('secret_note', '')
            repo_name = leakage.get('repo_name', '')
            file_path = leakage.get('file_path', '')
            file_url = leakage.get('file_url', '')
            scan_time = leakage.get('scan_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # 构建 Markdown 消息
            markdown_text = f"""## 🚨 密钥泄露告警

**密钥类型**: {secret_type}

**密钥值**: `{secret_masked}`

**备注**: {secret_note if secret_note else '无'}

**泄露仓库**: [{repo_name}]({file_url})

**泄露文件**: {file_path}

**发现时间**: {scan_time}

---

### ⚠️ 立即行动

1. 立即轮换该密钥
2. 检查密钥使用日志
3. 联系仓库所有者删除泄露代码
4. 评估影响范围

[查看详情]({file_url})
"""
            
            # 构建钉钉消息
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"🚨 {secret_type} 泄露告警",
                    "text": markdown_text
                },
                "at": {
                    "isAtAll": False
                }
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(data),
                timeout=10
            )
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print(f"  ✅ 已发送钉钉告警: {secret_type}")
                    return True
                else:
                    print(f"  ❌ 钉钉消息发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                print(f"  ❌ 钉钉请求失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ 发送钉钉消息异常: {e}")
            return False
    
    def send_batch_alert(self, leakages: List[Dict], statistics: Dict) -> bool:
        """
        发送批量泄露告警
        
        Args:
            leakages: 泄露列表
            statistics: 统计信息
            
        Returns:
            发送是否成功
        """
        if not self.enabled or not leakages:
            return False
        
        try:
            # 构建消息内容
            total_secrets = statistics.get('total_secrets', 0)
            leaked_secrets = statistics.get('leaked_secrets', 0)
            total_leakages = statistics.get('total_leakages', 0)
            unique_repos = statistics.get('unique_repos', 0)
            leakage_rate = statistics.get('leakage_rate', 0)
            
            # 构建前5个泄露的简要信息
            leak_summary = []
            for i, leakage in enumerate(leakages[:5], 1):
                secret_type = leakage.get('secret_type_display', '未知类型')
                repo_name = leakage.get('repo_name', '')
                leak_summary.append(f"{i}. {secret_type} - {repo_name}")
            
            leak_summary_text = "\n".join(leak_summary)
            if len(leakages) > 5:
                leak_summary_text += f"\n\n... 还有 {len(leakages) - 5} 处泄露"
            
            # 构建 Markdown 消息
            markdown_text = f"""## 🚨 密钥泄露监控报告

### 📊 扫描统计

- **总密钥数**: {total_secrets} 个
- **泄露密钥**: {leaked_secrets} 个
- **泄露位置**: {total_leakages} 处
- **泄露率**: {leakage_rate:.1f}%
- **涉及仓库**: {unique_repos} 个

---

### 🔍 泄露详情 (前5个)

{leak_summary_text}

---

### ⚠️ 建议操作

1. 立即轮换所有泄露的密钥
2. 检查密钥使用日志
3. 评估影响范围
4. 建立密钥管理规范

扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # 构建钉钉消息
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"🚨 发现 {leaked_secrets} 个密钥泄露",
                    "text": markdown_text
                },
                "at": {
                    "isAtAll": True  # @所有人
                }
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(data),
                timeout=10
            )
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print(f"✅ 已发送钉钉批量告警")
                    return True
                else:
                    print(f"❌ 钉钉消息发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                print(f"❌ 钉钉请求失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 发送钉钉消息异常: {e}")
            return False
    
    def send_success_message(self, statistics: Dict) -> bool:
        """
        发送扫描成功消息（未发现泄露）
        
        Args:
            statistics: 统计信息
            
        Returns:
            发送是否成功
        """
        if not self.enabled:
            return False
        
        try:
            total_secrets = statistics.get('total_secrets', 0)
            scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建 Markdown 消息
            markdown_text = f"""## ✅ 密钥泄露监控报告

### 📊 扫描结果

- **总密钥数**: {total_secrets} 个
- **泄露密钥**: 0 个
- **状态**: 安全

---

### 💡 建议

- 继续保持良好的安全实践
- 定期运行扫描检查
- 对团队进行安全培训

扫描时间: {scan_time}
"""
            
            # 构建钉钉消息
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "✅ 密钥监控：一切正常",
                    "text": markdown_text
                },
                "at": {
                    "isAtAll": False
                }
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(data),
                timeout=10
            )
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                return result.get('errcode') == 0
            return False
                
        except Exception as e:
            print(f"❌ 发送钉钉消息异常: {e}")
            return False

