#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML报告生成模块
"""
import os
from datetime import datetime
from typing import List, Dict
from config import OUTPUT_DIR


class HTMLReportGenerator:
    """HTML扫描报告生成器"""
    
    def __init__(self, output_dir: str = OUTPUT_DIR):
        """
        初始化HTML报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_monitor_report(self,
                                leakages: List[Dict],
                                statistics: Dict,
                                scan_start_time: datetime,
                                secrets_file: str) -> str:
        """
        生成监控模式HTML报告
        
        Args:
            leakages: 泄露列表
            statistics: 统计信息
            scan_start_time: 扫描开始时间
            secrets_file: 密钥清单文件路径
            
        Returns:
            报告文件路径
        """
        report_time = datetime.now()
        timestamp = report_time.strftime("%Y%m%d_%H%M%S")
        filename = f"monitor_report_{timestamp}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        # 计算扫描耗时
        duration = (report_time - scan_start_time).total_seconds()
        duration_str = f"{int(duration // 60)}分{int(duration % 60)}秒" if duration >= 60 else f"{int(duration)}秒"
        
        # 生成HTML
        html_content = self._generate_html(
            leakages=leakages,
            statistics=statistics,
            scan_start_time=scan_start_time,
            report_time=report_time,
            duration_str=duration_str,
            secrets_file=secrets_file
        )
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_html(self, leakages, statistics, scan_start_time, report_time, duration_str, secrets_file):
        """生成HTML内容"""
        
        # 状态标识
        if leakages:
            status_class = "danger"
            status_icon = "🚨"
            status_text = "发现泄露"
        else:
            status_class = "success"
            status_icon = "✅"
            status_text = "安全"
        
        # 泄露详情HTML
        leakages_html = self._generate_leakages_html(leakages)
        
        # 统计图表HTML
        charts_html = self._generate_charts_html(statistics)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>密钥泄露监控报告 - {report_time.strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        
        .status-banner {{
            padding: 30px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
        }}
        
        .status-banner.success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-banner.danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .info-card .label {{
            color: #6c757d;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        
        .info-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-box .number {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-box .label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .section {{
            margin: 40px 0;
        }}
        
        .section-title {{
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        
        .leakage-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .leakage-card:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        
        .leakage-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .leakage-title {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }}
        
        .risk-badge {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }}
        
        .risk-high {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .risk-medium {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .risk-low {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .leakage-detail {{
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 10px;
            margin: 10px 0;
        }}
        
        .detail-label {{
            font-weight: bold;
            color: #6c757d;
        }}
        
        .detail-value {{
            color: #333;
            word-break: break-all;
        }}
        
        .code-block {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            overflow-x: auto;
        }}
        
        .locations {{
            margin-top: 20px;
        }}
        
        .location-item {{
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 3px solid #667eea;
        }}
        
        .suggestions {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .suggestions h4 {{
            margin-bottom: 10px;
            color: #856404;
        }}
        
        .suggestions ul {{
            margin-left: 20px;
        }}
        
        .suggestions li {{
            margin: 5px 0;
            color: #856404;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px 40px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #e0e0e0;
        }}
        
        a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .no-leakage {{
            text-align: center;
            padding: 60px 20px;
        }}
        
        .no-leakage-icon {{
            font-size: 80px;
            margin-bottom: 20px;
        }}
        
        .no-leakage-text {{
            font-size: 24px;
            color: #28a745;
            margin-bottom: 10px;
        }}
        
        .no-leakage-desc {{
            color: #6c757d;
            font-size: 16px;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 密钥泄露监控报告</h1>
            <p class="subtitle">InCloud GitHub 密钥监控系统</p>
        </div>
        
        <div class="status-banner {status_class}">
            {status_icon} 扫描状态: {status_text}
        </div>
        
        <div class="content">
            <div class="section">
                <div class="info-grid">
                    <div class="info-card">
                        <div class="label">扫描模式</div>
                        <div class="value">密钥清单监控</div>
                    </div>
                    <div class="info-card">
                        <div class="label">清单文件</div>
                        <div class="value" style="font-size: 16px;">{os.path.basename(secrets_file)}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">扫描时间</div>
                        <div class="value" style="font-size: 18px;">{scan_start_time.strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">扫描耗时</div>
                        <div class="value">{duration_str}</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title">📊 扫描统计</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="number">{statistics['total_secrets']}</div>
                        <div class="label">总密钥数量</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">{statistics['leaked_secrets']}</div>
                        <div class="label">泄露密钥数</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">{statistics['total_leakages']}</div>
                        <div class="label">泄露位置数</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">{statistics['leakage_rate']:.1f}%</div>
                        <div class="label">泄露率</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">{statistics['unique_repos']}</div>
                        <div class="label">涉及仓库</div>
                    </div>
                </div>
            </div>
            
            {charts_html}
            
            {leakages_html}
        </div>
        
        <div class="footer">
            <p>报告生成时间: {report_time.strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p style="margin-top: 10px; color: #999;">SecretGuard © 2025</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def _generate_leakages_html(self, leakages: List[Dict]) -> str:
        """生成泄露详情HTML"""
        if not leakages:
            return """
            <div class="section">
                <div class="no-leakage">
                    <div class="no-leakage-icon">✅</div>
                    <div class="no-leakage-text">未发现密钥泄露</div>
                    <div class="no-leakage-desc">您清单中的所有密钥都未在 GitHub 公开仓库中发现</div>
                </div>
            </div>
            """
        
        # 按密钥分组
        grouped = {}
        for leakage in leakages:
            secret_value = leakage['secret_value']
            if secret_value not in grouped:
                grouped[secret_value] = []
            grouped[secret_value].append(leakage)
        
        html_parts = ['<div class="section">', '<h2 class="section-title">🚨 泄露详情</h2>']
        
        for idx, (secret_value, secret_leakages) in enumerate(grouped.items(), 1):
            first_leakage = secret_leakages[0]
            
            # 评估风险等级 - 所有泄露都是高风险
            risk_level = "高风险"
            risk_class = "risk-high"
            
            html_parts.append(f'''
            <div class="leakage-card">
                <div class="leakage-header">
                    <div class="leakage-title">[{idx}] {first_leakage['secret_type_display']}</div>
                    <div class="risk-badge {risk_class}">{risk_level}</div>
                </div>
                
                <div class="leakage-detail">
                    <div class="detail-label">密钥类型:</div>
                    <div class="detail-value">{first_leakage['secret_type_display']}</div>
                </div>
                
                <div class="leakage-detail">
                    <div class="detail-label">密钥值:</div>
                    <div class="detail-value"><code>{first_leakage['secret_masked']}</code></div>
                </div>
                
                {f'<div class="leakage-detail"><div class="detail-label">备注:</div><div class="detail-value">{first_leakage["secret_note"]}</div></div>' if first_leakage['secret_note'] else ''}
                
                <div class="leakage-detail">
                    <div class="detail-label">泄露位置:</div>
                    <div class="detail-value">{len(secret_leakages)} 处</div>
                </div>
                
                <div class="locations">
                    <strong>泄露位置详情:</strong>
            ''')
            
            for loc_idx, leakage in enumerate(secret_leakages, 1):
                # 根据类型显示不同的标签
                leak_type = leakage.get('type', 'Code')
                if leak_type == 'Code':
                    location_label = '文件'
                    detail_label = '行号'
                elif leak_type == 'Commits':
                    location_label = '提交'
                    detail_label = '位置'
                elif leak_type == 'Issue':
                    location_label = '议题'
                    detail_label = '位置'
                elif leak_type == 'Pull Request':
                    location_label = 'Pull Request'
                    detail_label = '位置'
                else:
                    location_label = '位置'
                    detail_label = '详情'
                
                html_parts.append(f'''
                    <div class="location-item">
                        <div><strong>位置 #{loc_idx}</strong></div>
                        <div style="margin-top: 10px;">
                            <strong>仓库:</strong> <a href="{leakage['file_url']}" target="_blank">{leakage['repo_name']}</a>
                            {f" ⭐ {leakage['repo_stars']}" if leakage.get('repo_stars', 0) > 0 else ''}
                        </div>
                        <div><strong>{location_label}:</strong> {leakage['file_path']}</div>
                        <div><strong>{detail_label}:</strong> {leakage['line_number']}</div>
                        <div class="code-block">{self._escape_html(leakage['line_content'][:150])}</div>
                        <div><a href="{leakage['file_url']}" target="_blank">查看完整代码 →</a></div>
                    </div>
                ''')
            
            html_parts.append('''
                </div>
                
                <div class="suggestions">
                    <h4>⚠️ 建议操作</h4>
                    <ul>
                        <li>立即轮换该密钥</li>
                        <li>检查密钥使用日志，确认是否有异常访问</li>
                        <li>联系仓库所有者删除泄露的代码</li>
                        <li>考虑使用 GitHub 密钥扫描删除请求</li>
                    </ul>
                </div>
            </div>
            ''')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def _generate_charts_html(self, statistics: Dict) -> str:
        """生成统计图表HTML"""
        if not statistics.get('by_type'):
            return ''
        
        html_parts = ['<div class="section">', '<h2 class="section-title">📈 密钥类型分布</h2>']
        html_parts.append('<div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">')
        
        for secret_type, info in sorted(statistics['by_type'].items(), key=lambda x: x[1]['count'], reverse=True):
            count = info['count']
            display_name = info['display_name']
            html_parts.append(f'''
            <div style="margin: 15px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>{display_name}</span>
                    <span><strong>{count}</strong> 处</span>
                </div>
                <div style="background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100%; width: {min(100, count * 10)}%;"></div>
                </div>
            </div>
            ''')
        
        html_parts.append('</div></div>')
        return '\n'.join(html_parts)
    
    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    def generate_monitor_summary(self, 
                                 report_path: str, 
                                 leakage_count: int,
                                 statistics: Dict) -> str:
        """
        生成监控模式扫描摘要
        
        Args:
            report_path: 报告文件路径
            leakage_count: 泄露数量
            statistics: 统计信息
            
        Returns:
            摘要文本
        """
        summary = []
        summary.append("")
        summary.append("=" * 60)
        summary.append("📊 监控完成摘要")
        summary.append("=" * 60)
        
        if leakage_count == 0:
            summary.append("✅ 状态: 安全")
            summary.append(f"   所有 {statistics['total_secrets']} 个密钥均未发现泄露")
        else:
            summary.append("⚠️  状态: 发现泄露")
            summary.append(f"   总密钥数: {statistics['total_secrets']} 个")
            summary.append(f"   泄露密钥: {statistics['leaked_secrets']} 个")
            summary.append(f"   泄露位置: {statistics['total_leakages']} 处")
            summary.append(f"   泄露率: {statistics['leakage_rate']:.1f}%")
            summary.append(f"   涉及仓库: {statistics['unique_repos']} 个")
        
        summary.append("")
        summary.append(f"📄 HTML报告: {report_path}")
        summary.append("=" * 60)
        
        return "\n".join(summary)

