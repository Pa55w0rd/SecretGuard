"""
配置文件 - SecretGuard 密钥泄露监控系统
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# GitHub配置
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

# 多Token支持（用逗号分隔）
GITHUB_TOKENS = os.getenv('GITHUB_TOKENS', '').split(',') if os.getenv('GITHUB_TOKENS') else []
# 合并单token和多tokens
ALL_GITHUB_TOKENS = list(filter(None, [GITHUB_TOKEN] + GITHUB_TOKENS))

# 扫描配置
SCAN_INTERVAL_HOURS = int(os.getenv('SCAN_INTERVAL_HOURS', 24))
OUTPUT_DIR = os.getenv('OUTPUT_DIR', './scan_reports')

# 要排除的文件扩展名
EXCLUDED_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
    '.mp4', '.avi', '.mov', '.wmv',
    '.zip', '.tar', '.gz', '.rar',
    '.exe', '.dll', '.so', '.dylib',
    '.pdf', '.doc', '.docx',
]

# 要排除的目录
EXCLUDED_DIRS = [
    'node_modules',
    '.git',
    'dist',
    'build',
    '__pycache__',
    'venv',
    'env',
]

# GitHub API速率限制
MAX_REPOS_PER_SEARCH = 100
SEARCH_DELAY_SECONDS = 2

# ===== 监控模式配置 =====
# 密钥清单文件（默认）
SECRETS_LIST_FILE = 'secrets_to_monitor.txt'

# 报告中显示密钥的前后字符数（隐藏中间部分）
SECRET_MASK_LENGTH = 6

# 每个密钥搜索间隔（秒），避免触发API速率限制
# GitHub 搜索 API 限制：每分钟 30 次
# 建议间隔：60秒/30次 = 2秒，为安全起见设为3秒
SEARCH_DELAY_PER_SECRET = 2

# 每个密钥最多返回结果数
MAX_RESULTS_PER_SECRET = 100

# 搜索类型配置
# 可选: 'code' (代码文件), 'commits' (提交记录), 'issues' (议题和PR)
# 默认只搜索代码文件，因为搜索多种类型会消耗更多API配额
DEFAULT_SEARCH_TYPES = ['code']  # 可以设置为 ['code', 'commits', 'issues'] 进行全面搜索
