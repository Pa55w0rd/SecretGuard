# 🔍 SecretGuard

<div align="center">

**GitHub 密钥泄露监控系统 - 守护您的密钥安全**

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/automation-GitHub%20Actions-2088FF.svg)](https://github.com/features/actions)

🚀 **完全基于 GitHub Actions，无需本地运行** | 💰 **公开仓库完全免费**

</div>

---

## 📖 简介

**SecretGuard** 是一个专业的 GitHub 密钥泄露监控系统，帮助您发现和防止敏感信息泄露到 GitHub 公开仓库。

### 🎯 核心功能

**密钥清单监控** - 精确搜索您的密钥是否泄露

- 提供一个密钥清单文件（如阿里云 AK/SK、AWS 密钥等）
- 系统在 GitHub 公开仓库中精确搜索这些密钥
- 支持搜索代码文件、提交记录、议题/PR
- 适用于企业安全团队、DevOps 团队监控自己的密钥

---

## ✨ 核心特性

- ✅ **精确搜索** - 直接搜索您提供的密钥字符串
- ✅ **多维度搜索** - 支持搜索代码文件、提交记录(commits)、议题/PR(issues)
- ✅ **多密钥类型** - 支持阿里云、AWS、腾讯云、Azure、API密钥、Token等
- ✅ **HTML报告** - 生成精美的HTML可视化报告，双击即可查看
- ✅ **即时告警** - 发现泄露立即发送钉钉消息通知，第一时间响应
- ✅ **多Token轮询** - 支持配置多个GitHub Token，自动轮询提升扫描速度
- ✅ **部分隐藏** - 报告中自动隐藏密钥中间部分保护安全
- ✅ **统计分析** - 按类型、仓库统计泄露情况
- ✅ **零配置运行** - 简单配置即可使用
- ✅ **全自动化** - 可配置定时自动扫描
- ✅ **GitHub Actions** - 云端运行，无需本地环境

---

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Pa55w0rd/SecretGuard.git
cd SecretGuard

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置Token
cp env.example .env
# 编辑 .env 文件，填入 GITHUB_TOKEN

# 4. 创建密钥清单
cp secrets_to_monitor.example.txt secrets_to_monitor.txt
# 编辑文件，格式：密钥类型|密钥值|备注

# 5. 运行扫描
python scan_github.py

# 6. 查看报告
# 双击打开 scan_reports/monitor_report_*.html
```

**可选配置**：
- 多Token轮询：`.env` 中配置 `GITHUB_TOKENS=token1,token2,token3`
- 钉钉告警：`.env` 中配置 `DINGTALK_WEBHOOK=https://oapi.dingtalk.com/...`
- 自动化：Fork 仓库，配置 GitHub Actions

---

## 📋 使用说明

### 基础用法

```bash
# 默认扫描（只搜索代码）
python scan_github.py

# 全面扫描（代码+提交+议题+PR）
python scan_github.py --search-types code commits issues pr

# 指定清单文件
python scan_github.py --secrets-list my_secrets.txt
```

### 密钥清单格式

```
# 格式: 密钥类型|密钥值|备注
aliyun_ak|LTAI5txxxxx|生产环境
aws_access_key|AKIAxxxxx|AWS主账号
custom|my-secret-token|自定义密钥
```

**支持的类型**：`aliyun_ak`、`aliyun_sk`、`aws_access_key`、`aws_secret_key`、`api_key`、`token`、`custom` 等

### 查看报告

报告保存在 `scan_reports/` 目录（HTML格式）：
- 📊 可视化统计
- 🚨 泄露详情（仓库/文件/行号）
- 💡 安全建议

---

## 📊 支持的密钥类型

**云平台**：阿里云、AWS、腾讯云、Azure、GCP  
**通用**：API密钥、Token、密码、私钥、证书  
**自定义**：任意密钥字符串

---

## 🔒 白名单配置

排除测试仓库、示例文件等不需要监控的泄露。

### 创建白名单

```bash
cp whitelist.yaml.example whitelist.yaml
# 编辑 whitelist.yaml
```

### 配置示例

```yaml
# 仓库白名单
repositories:
  - "mycompany/test-*"      # 测试仓库
  - "username/demo-project" # 演示项目

# 文件白名单
files:
  - "demo.py"               # 精确匹配根目录的 demo.py
  - "*demo*"                # 匹配文件名包含 demo
  - "test/**/*"             # test目录下的所有文件
  - "examples/**/*"         # examples目录下的所有文件
  - "**/*.md"               # 任意目录的Markdown文档
  - "**/test_*"             # 任意目录下test_开头的文件
```

**白名单规则**：
- 仓库名格式：`owner/repo`，支持通配符 `*`
- 文件路径支持 glob 模式：
  - `*` 匹配文件名中的任意字符（不包括 `/`）
  - `**` 匹配任意层级目录
  - `demo.py` 匹配根目录的精确文件
  - `*demo*` 匹配文件名包含 demo
  - `test/**/*` 匹配 test 目录下所有文件
- 匹配白名单的泄露将被自动过滤

---

## 🛡️ 发现泄露后的处理

### 立即行动

1. **轮换密钥** - 登录云服务控制台，删除旧密钥，生成新密钥
2. **检查日志** - 查看API调用记录，确认是否被滥用
3. **清理历史** - 使用 [git-filter-repo](https://github.com/newren/git-filter-repo) 从Git历史删除

### 长期防护

- ✅ 使用环境变量或密钥管理服务
- ✅ 配置 `.gitignore` 排除敏感文件  
- ✅ 设置 Git pre-commit hooks
- ✅ 定期运行此工具监控

---

## ❓ 常见问题

**Q: 密钥会被上传吗？**  
A: 不会。只在本地/GitHub Actions运行，不上传任何第三方。

**Q: API限制怎么办？**  
A: 配置多个Token轮询：`.env` 中 `GITHUB_TOKENS=token1,token2,token3`  
3个Token = 90次/分钟，自动切换无需等待。

**Q: 发现泄露怎么办？**  
A: 1) 立即轮换密钥 2) 清理Git历史 3) 检查日志

**Q: 支持私有仓库吗？**  
A: 支持，Token需 `repo` 权限（谨慎使用）。

---

## 🔧 配套工具

**云密钥批量收集**: [cloud_ak_collector](https://github.com/Pa55w0rd/Cloud-AK-Collector)  
支持华为云、阿里云、Authing，一键获取所有用户AK/SK

---

<div align="center">

**⭐ 如果有用，欢迎 Star！**

[GitHub](https://github.com/Pa55w0rd/SecretGuard) • [文档](./README.md) • [问题反馈](https://github.com/Pa55w0rd/SecretGuard/issues)

MIT License © 2025

</div>
