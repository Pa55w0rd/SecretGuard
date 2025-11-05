"""
GitHub仓库扫描模块 - 密钥泄露精确搜索
"""
import time
from datetime import datetime
from typing import List, Dict, Optional
from github import Github, GithubException
from config import GITHUB_TOKEN, SEARCH_DELAY_SECONDS


class GitHubScanner:
    """GitHub仓库扫描器"""
    
    def __init__(self, token: str = GITHUB_TOKEN, token_manager=None):
        """
        初始化GitHub扫描器
        
        Args:
            token: GitHub Personal Access Token
            token_manager: GitHubTokenManager实例（可选，用于多Token轮询）
        """
        if not token:
            raise ValueError("GitHub Token is required. Please set GITHUB_TOKEN in .env file")
        
        self.token_manager = token_manager
        self.current_token = token
        
        # 配置超时和重试参数，避免长时间等待
        self.github = Github(
            token,
            timeout=30,  # 设置30秒超时
            retry=None   # 禁用自动重试，我们自己处理
        )
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        
    def get_rate_limit_info(self) -> Dict:
        """获取API速率限制信息"""
        rate_limit = self.github.get_rate_limit()
        core = rate_limit.core
        
        return {
            'remaining': core.remaining,
            'limit': core.limit,
            'reset': core.reset
        }
    
    def switch_token_if_needed(self, force=False):
        """检查配额并在需要时切换Token
        
        Args:
            force: 强制切换到下一个Token（不检查当前配额）
            
        Returns:
            True: 成功切换到新Token
            False: 不需要切换（配额充足或只有1个Token）
        """
        if not self.token_manager:
            return False
        
        try:
            # 如果不是强制切换，检查是否需要切换
            if not force:
                rate_limit = self.github.get_rate_limit()
                search_limit = rate_limit.search
                
                # 配额充足，不需要切换
                if search_limit.remaining > 2:
                    return False
                
                print(f"  ⚠️  当前Token配额不足 (剩余: {search_limit.remaining})")
            
            # 获取下一个Token（循环轮询）
            old_token = self.current_token
            new_token = self.token_manager.get_next_token()
            
            # 如果新Token和当前Token相同，说明只有1个Token
            if new_token == old_token:
                return False
            
            # 切换到新Token
            print(f"  ✅ 切换到下一个Token...")
            self.current_token = new_token
            
            # 重新创建Github实例
            self.github = Github(
                new_token,
                timeout=30,
                retry=None
            )
            return True
            
        except Exception as e:
            print(f"  ⚠️  检查配额失败: {e}")
            return False
    
    def wait_for_rate_limit(self):
        """等待速率限制重置"""
        # 先尝试切换Token
        if self.switch_token_if_needed():
            return
        
        # 如果切换失败，才等待
        info = self.get_rate_limit_info()
        if info['remaining'] < 10:
            # info['reset'] 是 datetime 对象，需要和 datetime.now() 比较
            wait_time = (info['reset'] - datetime.now()).total_seconds() + 10
            print(f"⚠️  API速率限制即将耗尽，等待 {wait_time:.0f} 秒...")
            time.sleep(max(0, wait_time))
    
    def display_rate_limit(self):
        """显示当前 API 速率限制状态"""
        try:
            rate_limit = self.github.get_rate_limit()
            
            # 核心 API 限制
            core = rate_limit.core
            print(f"📊 核心 API 限制: {core.remaining}/{core.limit} 剩余")
            if core.remaining < 100:
                reset_time = core.reset.strftime('%H:%M:%S')
                print(f"   ⚠️  剩余次数较少，将在 {reset_time} 重置")
            
            # 搜索 API 限制 (重要！)
            search = rate_limit.search
            print(f"🔍 搜索 API 限制: {search.remaining}/{search.limit} 剩余")
            if search.remaining < 10:
                reset_time = search.reset.strftime('%H:%M:%S')
                reset_seconds = (search.reset - datetime.now()).total_seconds()
                print(f"   ⚠️  搜索配额不足，将在 {reset_time} 重置（约 {int(reset_seconds)} 秒后）")
            
        except Exception as e:
            print(f"   ℹ️  无法获取速率限制信息: {e}")
    
    def get_file_content(self, repo_full_name: str, file_path: str) -> Optional[str]:
        """
        获取文件内容
        
        Args:
            repo_full_name: 仓库全名 (owner/repo)
            file_path: 文件路径
            
        Returns:
            文件内容（文本）
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            content = repo.get_contents(file_path)
            
            # 解码内容
            try:
                return content.decoded_content.decode('utf-8')
            except UnicodeDecodeError:
                # 如果是二进制文件，返回None
                return None
        except GithubException as e:
            # 403 错误直接跳过，不打印错误
            if e.status == 403:
                pass  # 静默跳过
            return None
    
    def search_secret_leakage(self, secret_value: str, max_results: int = 100, max_retries: int = 3, 
                             search_types: List[str] = ['code']) -> List[Dict]:
        """
        精确搜索指定密钥是否泄露到GitHub
        
        Args:
            secret_value: 要搜索的密钥值
            max_results: 最多返回结果数
            max_retries: 最大重试次数
            search_types: 搜索类型列表，可选: 'code', 'commits', 'issues'
            
        Returns:
            泄露位置列表，每个包含仓库、文件、行号等信息
        """
        all_results = []
        
        for search_type in search_types:
            results = self._search_by_type(secret_value, search_type, max_results, max_retries)
            all_results.extend(results)
        
        return all_results
    
    def _search_by_type(self, secret_value: str, search_type: str, max_results: int, max_retries: int) -> List[Dict]:
        """
        按类型搜索密钥泄露
        
        Args:
            secret_value: 要搜索的密钥值
            search_type: 搜索类型 ('code', 'commits', 'issues', 'pr')
            max_results: 最多返回结果数
            max_retries: 最大重试次数
            
        Returns:
            泄露位置列表
        """
        results = []
        
        for attempt in range(max_retries):
            try:
                # 使用GitHub Code Search API精确搜索
                # 注意：某些特殊字符需要用引号包裹
                search_query = f'"{secret_value}"'
                
                if attempt > 0:
                    print(f"  🔄 重试第 {attempt} 次...")
                else:
                    # 根据搜索类型显示不同的提示
                    type_emoji = {
                        'code': '📄',
                        'commits': '💾', 
                        'issues': '🔖',
                        'pr': '🔀'
                    }
                    type_name = {
                        'code': 'Code',
                        'commits': 'Commits',
                        'issues': 'Issues',
                        'pr': 'Pull Requests'
                    }
                    emoji = type_emoji.get(search_type, '🔎')
                    name = type_name.get(search_type, search_type)
                    print(f"  {emoji} 搜索 {name}...")
                
                # 在搜索前主动检查速率限制并切换Token（如果需要）
                if self.token_manager:
                    try:
                        rate_limit = self.github.get_rate_limit()
                        search_limit = rate_limit.search
                        if search_limit.remaining <= 2:
                            print(f"  ⚠️  当前Token搜索配额不足 ({search_limit.remaining}/{search_limit.limit})")
                            print(f"  🔄 主动切换到下一个Token...")
                            if not self.switch_token_if_needed():
                                # 切换失败，说明只有1个Token（继续执行，让API调用触发限制异常后再等待）
                                pass
                    except Exception:
                        pass  # 检查失败，继续执行
                
                # 根据类型选择不同的搜索API
                if search_type == 'code':
                    search_results = self.github.search_code(search_query)
                elif search_type == 'commits':
                    search_results = self.github.search_commits(search_query)
                    # 调试：显示找到的commits数量
                    try:
                        total_count = search_results.totalCount
                        if total_count > 0:
                            print(f"  ℹ️  搜索API返回 {total_count} 个commits，正在检查差异...")
                    except:
                        pass
                elif search_type == 'issues' or search_type == 'pr':
                    # issues 和 pr 都使用 search_issues API，但后续处理会过滤
                    search_results = self.github.search_issues(search_query)
                else:
                    print(f"  ⚠️  未知的搜索类型: {search_type}")
                    return []
                
                # 根据类型处理搜索结果
                if search_type == 'code':
                    results = self._process_code_results(search_results, secret_value, max_results)
                elif search_type == 'commits':
                    results = self._process_commit_results(search_results, secret_value, max_results)
                elif search_type == 'issues':
                    results = self._process_issue_results(search_results, secret_value, max_results, only_issues=True)
                elif search_type == 'pr':
                    results = self._process_issue_results(search_results, secret_value, max_results, only_pr=True)
                
                # 搜索成功，跳出重试循环
                if results:
                    print(f"  ⚠️  发现 {len(results)} 处泄露")
                else:
                    print(f"  ✅ 未发现泄露")
                break
                
            except GithubException as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower():
                    print(f"  ⚠️  触发 GitHub 搜索 API 速率限制")
                    
                    # 如果配置了token_manager，尝试切换Token
                    if self.token_manager:
                        print(f"  🔄 切换到下一个Token...")
                        if self.switch_token_if_needed(force=True):
                            # 切换成功，重试当前请求（不计入重试次数）
                            continue
                        else:
                            # 切换失败，说明只有1个Token
                            print(f"  ⚠️  只有1个Token，需要等待重置")
                    
                    # 没有token_manager或只有1个Token，等待重置
                    print(f"     （GitHub 限制：每分钟最多 30 次搜索）")
                    if attempt < max_retries - 1:
                        # 检查实际的重置时间
                        try:
                            rate_limit = self.github.get_rate_limit()
                            search_limit = rate_limit.search
                            if search_limit.remaining == 0:
                                wait_time = (search_limit.reset - datetime.now()).total_seconds() + 5
                                wait_time = max(60, min(wait_time, 70))  # 限制在60-70秒之间
                                print(f"     等待 {int(wait_time)} 秒后重试...")
                                time.sleep(wait_time)
                            else:
                                wait_time = 60
                                print(f"     等待 {wait_time} 秒后重试...")
                                time.sleep(wait_time)
                        except:
                            wait_time = 60
                            print(f"     等待 {wait_time} 秒后重试...")
                            time.sleep(wait_time)
                    else:
                        print(f"     已达到最大重试次数，跳过此密钥")
                elif "403" in error_msg:
                    print(f"  ⚠️  搜索被限制（403）")
                    break  # 403 错误不重试
                else:
                    print(f"  ⚠️  搜索失败: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(5)  # 等待5秒后重试
                    else:
                        break
            except Exception as e:
                print(f"  ❌ 搜索出错: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    break
        
        return results
    
    def _process_code_results(self, search_results, secret_value: str, max_results: int) -> List[Dict]:
        """处理代码搜索结果"""
        results = []
        count = 0
        
        for code in search_results:
            if count >= max_results:
                break
            
            try:
                # 获取文件内容以确认匹配和获取行号
                content = self.get_file_content(code.repository.full_name, code.path)
                
                if content and secret_value in content:
                    # 找到包含密钥的行
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if secret_value in line:
                            results.append({
                                'type': 'Code',
                                'repo_name': code.repository.full_name,
                                'repo_url': code.repository.html_url,
                                'file_path': code.path,
                                'file_url': code.html_url,
                                'line_number': line_num,
                                'line_content': line.strip(),
                                'repo_owner': code.repository.owner.login,
                                'repo_description': code.repository.description,
                                'repo_updated_at': code.repository.updated_at,
                                'repo_stars': code.repository.stargazers_count,
                            })
                    count += 1
            
            except Exception:
                # 跳过获取失败的文件
                continue
        
        return results
    
    def _process_commit_results(self, search_results, secret_value: str, max_results: int) -> List[Dict]:
        """处理提交搜索结果
        
        GitHub search_commits API会返回提交消息或差异中包含密钥的commits。
        """
        results = []
        count = 0
        processed = 0
        
        print(f"  ℹ️  开始处理commits结果...")
        
        for commit in search_results:
            if count >= max_results:
                break
            
            processed += 1
            if processed > 30:  # 最多检查30个commits
                print(f"  ⚠️  已达到最大处理数量(30)，停止检查")
                break
            
            try:
                # GitHub search_commits 返回的对象可能没有 repository 属性
                # 需要从 commit 的 html_url 中提取仓库信息
                commit_sha_short = commit.sha[:7]
                
                # 从 html_url 提取仓库名: https://github.com/owner/repo/commit/sha
                try:
                    html_url = commit.html_url
                    # 解析: https://github.com/owner/repo/commit/sha
                    parts = html_url.replace('https://github.com/', '').split('/')
                    repo_name = f"{parts[0]}/{parts[1]}"
                except:
                    print(f"     ❌ 无法解析仓库名")
                    continue
                
                print(f"  📝 [{processed}] 检查 commit {commit_sha_short} ({repo_name})")
                
                # 先检查消息中是否有密钥
                commit_message = commit.commit.message if commit.commit and commit.commit.message else ""
                found_in_message = secret_value in commit_message
                
                if found_in_message:
                    print(f"     ✓ 在消息中找到密钥")
                
                # 获取完整的commit对象以检查diff
                found_in_diff = False
                affected_files = []
                
                try:
                    repo_obj = self.github.get_repo(repo_name)
                    full_commit = repo_obj.get_commit(commit.sha)
                    
                    # 检查每个文件的patch
                    files_count = len(full_commit.files) if hasattr(full_commit, 'files') and full_commit.files else 0
                    print(f"     📁 检查 {files_count} 个文件的差异...")
                    
                    if files_count > 0:
                        for file in full_commit.files:
                            file_name = file.filename if hasattr(file, 'filename') else 'unknown'
                            
                            if hasattr(file, 'patch') and file.patch:
                                if secret_value in file.patch:
                                    found_in_diff = True
                                    affected_files.append(file_name)
                                    print(f"     ✓ 在文件 {file_name} 的差异中找到密钥")
                    else:
                        print(f"     ⚠️  此commit没有文件变更")
                    
                    # 获取仓库信息
                    repo_url = repo_obj.html_url
                    repo_owner = repo_obj.owner.login
                    repo_description = repo_obj.description
                    repo_updated_at = repo_obj.updated_at
                    repo_stars = repo_obj.stargazers_count
                        
                except Exception as e:
                    print(f"     ❌ 获取commit详情失败: {str(e)[:100]}")
                    # 即使获取详情失败，如果消息中有密钥，也应该记录
                    if not found_in_message:
                        continue
                    # 使用默认值
                    repo_url = f"https://github.com/{repo_name}"
                    repo_owner = repo_name.split('/')[0]
                    repo_description = None
                    repo_updated_at = None
                    repo_stars = 0
                
                # 如果在消息或差异中找到密钥，记录结果
                if found_in_message or found_in_diff:
                    found_in = []
                    if found_in_message:
                        found_in.append('Message')
                    if found_in_diff:
                        found_in.append('Diff')
                    
                    print(f"     ✅ 找到泄露，位置: {' + '.join(found_in)}")
                    
                    result = {
                        'type': 'Commits',
                        'repo_name': repo_name,
                        'repo_url': repo_url,
                        'commit_sha': commit_sha_short,
                        'commit_url': commit.html_url,
                        'file_url': commit.html_url,
                        'file_path': f"Commit {commit_sha_short}",
                        'line_number': ' + '.join(found_in),
                        'line_content': commit_message.strip()[:150],
                        'commit_message': commit_message.strip()[:200],
                        'author': commit.commit.author.name if commit.commit and commit.commit.author else '未知',
                        'committed_date': commit.commit.author.date if commit.commit and commit.commit.author else None,
                        'repo_owner': repo_owner,
                        'repo_description': repo_description,
                        'repo_updated_at': repo_updated_at,
                        'repo_stars': repo_stars,
                    }
                    
                    if affected_files:
                        result['affected_files'] = ', '.join(affected_files[:5])
                    
                    results.append(result)
                    count += 1
                else:
                    print(f"     ⚠️  未找到密钥（可能是误报）")
                    
            except Exception as e:
                print(f"     ❌ 处理commit时出错: {str(e)[:100]}")
                continue
        
        print(f"  ℹ️  处理完成，共找到 {len(results)} 处泄露")
        return results
    
    def _process_issue_results(self, search_results, secret_value: str, max_results: int, 
                              only_issues: bool = False, only_pr: bool = False) -> List[Dict]:
        """处理议题/PR搜索结果
        
        Args:
            search_results: 搜索结果
            secret_value: 密钥值
            max_results: 最大结果数
            only_issues: 只返回Issue（不含PR）
            only_pr: 只返回PR（不含Issue）
        """
        results = []
        count = 0
        
        for issue in search_results:
            if count >= max_results:
                break
            
            try:
                # 判断是 Issue 还是 Pull Request
                is_pr = issue.pull_request is not None
                issue_type = 'Pull Request' if is_pr else 'Issue'
                
                # 根据过滤条件跳过
                if only_issues and is_pr:
                    continue  # 只要Issue，跳过PR
                if only_pr and not is_pr:
                    continue  # 只要PR，跳过Issue
                
                # 检查密钥在标题还是内容中
                found_in = []
                if secret_value in issue.title:
                    found_in.append('标题')
                if issue.body and secret_value in issue.body:
                    found_in.append('内容')
                
                results.append({
                    'type': issue_type,
                    'repo_name': issue.repository.full_name,
                    'repo_url': issue.repository.html_url,
                    'issue_number': issue.number,
                    'issue_url': issue.html_url,
                    'file_url': issue.html_url,  # 使用issue_url作为file_url
                    'file_path': f"{issue_type} #{issue.number}",  # 议题编号作为路径
                    'line_number': ', '.join(found_in) if found_in else '内容',  # 显示在标题还是内容中
                    'line_content': issue.title[:150],  # 使用标题作为内容
                    'issue_title': issue.title,
                    'issue_state': issue.state,
                    'found_in': ', '.join(found_in) if found_in else '内容',
                    'created_at': issue.created_at,
                    'author': issue.user.login if issue.user else '未知',
                    'repo_owner': issue.repository.owner.login,
                    'repo_description': issue.repository.description,
                    'repo_updated_at': issue.repository.updated_at,
                    'repo_stars': issue.repository.stargazers_count,
                })
                count += 1
            
            except Exception:
                # 跳过处理失败的议题
                continue
        
        return results
