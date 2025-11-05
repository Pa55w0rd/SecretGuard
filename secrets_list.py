"""
密钥清单管理模块
用于加载和解析用户提供的密钥清单文件
"""
import os
from typing import List, Dict, Optional


class SecretItem:
    """密钥项数据类"""
    
    def __init__(self, secret_type: str, secret_value: str, note: str = ""):
        """
        初始化密钥项
        
        Args:
            secret_type: 密钥类型
            secret_value: 密钥值
            note: 备注信息
        """
        self.secret_type = secret_type
        self.secret_value = secret_value
        self.note = note
    
    def mask_value(self, mask_length: int = 6) -> str:
        """
        返回部分隐藏的密钥值
        
        Args:
            mask_length: 显示的前后字符数
            
        Returns:
            隐藏后的密钥值，如: LTAI5t******gYov
        """
        value = self.secret_value
        if len(value) <= mask_length * 2:
            # 如果密钥太短，只显示开头
            return value[:mask_length] + "******"
        return value[:mask_length] + "******" + value[-mask_length:]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'type': self.secret_type,
            'value': self.secret_value,
            'note': self.note,
            'masked_value': self.mask_value()
        }
    
    def __repr__(self):
        return f"SecretItem(type={self.secret_type}, value={self.mask_value()}, note={self.note})"


class SecretsListLoader:
    """密钥清单加载器"""
    
    # 支持的密钥类型
    SUPPORTED_TYPES = [
        'aliyun_ak', 'aliyun_sk',           # 阿里云
        'huaweicloud_ak', 'huaweicloud_sk', # 华为云
        'authing_app',                       # Authing应用ID
        'cloud_ak',                          # 通用云平台AK
        'aws_access_key', 'aws_secret_key',  # AWS
        'tencent_secret_id', 'tencent_secret_key',  # 腾讯云
        'azure_key',                         # Azure
        'gcp_key',                           # Google Cloud
        'api_key',                           # 通用API密钥
        'token',                             # 通用Token
        'password',                          # 密码
        'private_key',                       # 私钥
        'certificate',                       # 证书
        'custom'                             # 自定义类型
    ]
    
    def __init__(self):
        """初始化加载器"""
        self.secrets: List[SecretItem] = []
        self.errors: List[str] = []
    
    def load_from_file(self, file_path: str) -> List[SecretItem]:
        """
        从文件加载密钥清单
        
        Args:
            file_path: 清单文件路径
            
        Returns:
            密钥项列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"密钥清单文件不存在: {file_path}\n"
                f"   提示: 可以复制 secrets_to_monitor.example.txt 为起点"
            )
        
        self.secrets = []
        self.errors = []
        total_lines = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析行
                try:
                    secret_item = self._parse_line(line, line_num)
                    if secret_item:
                        self.secrets.append(secret_item)
                except ValueError as e:
                    error_msg = f"第 {line_num} 行: {e}"
                    self.errors.append(error_msg)
                    print(f"⚠️  {error_msg}")
        
        if not self.secrets and not self.errors:
            raise ValueError(
                f"密钥清单文件为空或没有有效的密钥: {file_path}\n"
                f"   文件共 {total_lines} 行，但没有找到有效的密钥配置\n"
                f"   请检查文件格式是否正确（格式: 密钥类型|密钥值|备注）"
            )
        
        if not self.secrets and self.errors:
            raise ValueError(
                f"密钥清单文件包含 {len(self.errors)} 个错误，没有成功加载任何密钥\n"
                f"   请修复上述错误后重试"
            )
        
        return self.secrets
    
    def _parse_line(self, line: str, line_num: int) -> Optional[SecretItem]:
        """
        解析单行数据
        
        格式: 密钥类型|密钥值|备注(可选)
        
        Args:
            line: 行内容
            line_num: 行号
            
        Returns:
            SecretItem对象或None
            
        Raises:
            ValueError: 格式错误
        """
        parts = line.split('|')
        
        if len(parts) < 2:
            raise ValueError(f"格式错误，需要至少2个字段（密钥类型|密钥值），当前只有 {len(parts)} 个字段")
        
        secret_type = parts[0].strip()
        secret_value = parts[1].strip()
        note = parts[2].strip() if len(parts) > 2 else ""
        
        # 验证密钥类型
        if secret_type not in self.SUPPORTED_TYPES:
            print(f"⚠️  第 {line_num} 行: 未知的密钥类型 '{secret_type}'，将作为 'custom' 类型处理")
            # 不抛出错误，而是将其视为自定义类型
        
        # 验证密钥值
        if not secret_value:
            raise ValueError("密钥值不能为空")
        
        if len(secret_value) < 4:
            raise ValueError(f"密钥值太短（至少4个字符），当前长度: {len(secret_value)}")
        
        return SecretItem(secret_type, secret_value, note)
    
    def get_secrets_by_type(self, secret_type: str) -> List[SecretItem]:
        """
        按类型获取密钥
        
        Args:
            secret_type: 密钥类型
            
        Returns:
            符合类型的密钥列表
        """
        return [s for s in self.secrets if s.secret_type == secret_type]
    
    def get_all_secrets(self) -> List[SecretItem]:
        """获取所有密钥"""
        return self.secrets
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        type_counts = {}
        for secret in self.secrets:
            type_counts[secret.secret_type] = type_counts.get(secret.secret_type, 0) + 1
        
        return {
            'total_count': len(self.secrets),
            'type_counts': type_counts,
            'error_count': len(self.errors)
        }
    
    def validate_format(self, file_path: str) -> tuple[bool, List[str]]:
        """
        验证文件格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否有效, 错误列表)
        """
        try:
            self.load_from_file(file_path)
            return len(self.secrets) > 0, self.errors
        except Exception as e:
            return False, [str(e)]
    
    def print_summary(self):
        """打印加载摘要"""
        stats = self.get_statistics()
        print(f"\n📋 密钥清单加载摘要:")
        print(f"   总数量: {stats['total_count']}")
        print(f"   错误数: {stats['error_count']}")
        
        if stats['type_counts']:
            print(f"\n   按类型统计:")
            for secret_type, count in sorted(stats['type_counts'].items()):
                print(f"     - {secret_type}: {count}")


# 类型名称映射（用于报告显示）
SECRET_TYPE_NAMES = {
    'aliyun_ak': '阿里云 AccessKey',
    'aliyun_sk': '阿里云 SecretKey',
    'huaweicloud_ak': '华为云 AccessKey',
    'huaweicloud_sk': '华为云 SecretKey',
    'authing_app': 'Authing 应用ID',
    'cloud_ak': '云平台 AccessKey',
    'aws_access_key': 'AWS Access Key',
    'aws_secret_key': 'AWS Secret Key',
    'tencent_secret_id': '腾讯云 SecretId',
    'tencent_secret_key': '腾讯云 SecretKey',
    'azure_key': 'Azure 密钥',
    'gcp_key': 'Google Cloud 密钥',
    'api_key': 'API 密钥',
    'token': 'Token',
    'password': '密码',
    'private_key': '私钥',
    'certificate': '证书',
    'custom': '自定义密钥'
}


def get_type_display_name(secret_type: str) -> str:
    """
    获取密钥类型的显示名称
    
    Args:
        secret_type: 密钥类型
        
    Returns:
        显示名称
    """
    return SECRET_TYPE_NAMES.get(secret_type, secret_type)

