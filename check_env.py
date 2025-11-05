#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置检查工具
用于诊断GitHub Token配置问题
"""

import os
from dotenv import load_dotenv

print("=" * 80)
print("环境配置诊断工具")
print("=" * 80)
print()

# 加载环境变量
load_dotenv()

# 检查.env文件是否存在
env_file = '.env'
if os.path.exists(env_file):
    print(f"✅ 找到配置文件: {env_file}")
    print()
    
    # 读取并显示（隐藏敏感信息）
    print("📄 文件内容预览:")
    print("-" * 80)
    with open(env_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                print(f"{line_num:3}: {line}")
            elif 'TOKEN' in line.upper():
                # 隐藏token值
                if '=' in line:
                    key, value = line.split('=', 1)
                    if value.strip():
                        masked = value[:10] + '...' + value[-4:] if len(value) > 14 else '***'
                        print(f"{line_num:3}: {key}={masked}")
                    else:
                        print(f"{line_num:3}: {key}=（空值）")
                else:
                    print(f"{line_num:3}: {line}")
            else:
                print(f"{line_num:3}: {line}")
    print("-" * 80)
    print()
else:
    print(f"❌ 未找到配置文件: {env_file}")
    print(f"   请复制 env.example 为 .env")
    print()

# 检查环境变量
print("🔍 环境变量检查:")
print("-" * 80)

github_token = os.getenv('GITHUB_TOKEN', '')
github_tokens = os.getenv('GITHUB_TOKENS', '')

print(f"GITHUB_TOKEN: ", end='')
if github_token:
    masked = github_token[:10] + '...' + github_token[-4:]
    print(f"✅ 已设置 ({masked})")
else:
    print("❌ 未设置")

print(f"GITHUB_TOKENS: ", end='')
if github_tokens:
    tokens = [t.strip() for t in github_tokens.split(',') if t.strip()]
    print(f"✅ 已设置 ({len(tokens)} 个token)")
    for i, token in enumerate(tokens, 1):
        masked = token[:10] + '...' + token[-4:] if len(token) > 14 else '***'
        print(f"  Token {i}: {masked}")
else:
    print("❌ 未设置")

print("-" * 80)
print()

# 统计总token数
all_tokens = []
if github_token:
    all_tokens.append(github_token)
if github_tokens:
    all_tokens.extend([t.strip() for t in github_tokens.split(',') if t.strip()])

# 去重
unique_tokens = list(dict.fromkeys(all_tokens))

print("📊 Token统计:")
print("-" * 80)
print(f"单token (GITHUB_TOKEN): {1 if github_token else 0} 个")
print(f"多token (GITHUB_TOKENS): {len([t.strip() for t in github_tokens.split(',') if t.strip()]) if github_tokens else 0} 个")
print(f"总计（去重后）: {len(unique_tokens)} 个")
print("-" * 80)
print()

if len(unique_tokens) == 0:
    print("❌ 问题: 没有配置任何Token")
    print()
    print("解决方案:")
    print("1. 在 https://github.com/settings/tokens 创建Token")
    print("2. 在 .env 文件中配置:")
    print("   GITHUB_TOKEN=ghp_your_token_here")
    print("   或")
    print("   GITHUB_TOKENS=ghp_token1,ghp_token2")
elif len(unique_tokens) == 1:
    print("⚠️  提示: 只配置了1个Token")
    print()
    print("优化建议:")
    print("1. 创建更多Token以提高扫描速度")
    print("2. 在 .env 文件中添加:")
    print("   GITHUB_TOKENS=ghp_token1,ghp_token2,ghp_token3")
    print()
    print("注意: Token之间用英文逗号分隔，不要有空格")
else:
    print(f"✅ 配置正确: 共 {len(unique_tokens)} 个Token")
    print()
    print("提示:")
    print(f"- 理论最大速率: {len(unique_tokens) * 30} 次/分钟")
    print(f"- 建议用于监控: {len(unique_tokens) * 300} 个密钥以内")

print()
print("=" * 80)
print("检查完成")
print("=" * 80)

