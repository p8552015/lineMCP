#!/usr/bin/env python3
"""
版本管理工具
用於管理專案版本和生成 changelog
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import re

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        import toml as tomllib


class VersionManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.bot_dir = project_root / "apps" / "bot"
        self.pyproject_path = self.bot_dir / "pyproject.toml"
        self.changelog_path = project_root / "CHANGELOG.md"
    
    def get_current_version(self) -> str:
        """獲取當前版本"""
        try:
            result = subprocess.run(
                ["poetry", "version", "-s"],
                cwd=self.bot_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ 無法獲取當前版本: {e}")
            sys.exit(1)
    
    def bump_version(self, bump_type: str) -> str:
        """升級版本"""
        print(f"📈 升級版本 ({bump_type})...")
        
        try:
            # 升級版本
            result = subprocess.run(
                ["poetry", "version", bump_type],
                cwd=self.bot_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            # 獲取新版本
            new_version = self.get_current_version()
            print(f"✅ 版本已升級到: {new_version}")
            return new_version
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 版本升級失敗: {e}")
            sys.exit(1)
    
    def get_git_commits_since_tag(self, since_tag: str = None) -> list:
        """獲取自指定標籤以來的提交記錄"""
        if since_tag:
            cmd = ["git", "log", f"{since_tag}..HEAD", "--pretty=format:%h|%s|%an|%ad", "--date=short"]
        else:
            cmd = ["git", "log", "--pretty=format:%h|%s|%an|%ad", "--date=short"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        commits.append({
                            'hash': parts[0],
                            'message': parts[1],
                            'author': parts[2],
                            'date': parts[3]
                        })
            return commits
        except subprocess.CalledProcessError:
            return []
    
    def get_latest_tag(self) -> str:
        """獲取最新標籤"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
    
    def categorize_commits(self, commits: list) -> dict:
        """將提交記錄分類"""
        categories = {
            'features': [],
            'fixes': [],
            'improvements': [],
            'docs': [],
            'tests': [],
            'chores': [],
            'security': [],
            'breaking': []
        }
        
        for commit in commits:
            message = commit['message'].lower()
            
            # 檢查重大變更
            if 'breaking' in message or 'BREAKING CHANGE' in commit['message']:
                categories['breaking'].append(commit)
            # 新功能
            elif any(word in message for word in ['feat:', 'feature:', 'add:', 'new:']):
                categories['features'].append(commit)
            # 錯誤修復
            elif any(word in message for word in ['fix:', 'bug:', 'patch:', 'hotfix:']):
                categories['fixes'].append(commit)
            # 改進
            elif any(word in message for word in ['improve:', 'enhance:', 'update:', 'refactor:', 'perf:']):
                categories['improvements'].append(commit)
            # 文檔
            elif any(word in message for word in ['docs:', 'doc:', 'readme:', 'documentation:']):
                categories['docs'].append(commit)
            # 測試
            elif any(word in message for word in ['test:', 'tests:', 'testing:']):
                categories['tests'].append(commit)
            # 安全
            elif any(word in message for word in ['security:', 'sec:', 'vulnerability:', 'cve:']):
                categories['security'].append(commit)
            # 雜項
            else:
                categories['chores'].append(commit)
        
        return categories
    
    def generate_changelog_entry(self, version: str, categories: dict) -> str:
        """生成 changelog 條目"""
        date = datetime.now().strftime("%Y-%m-%d")
        entry = f"## [{version}] - {date}\n\n"
        
        if categories['breaking']:
            entry += "### ⚠️ BREAKING CHANGES\n"
            for commit in categories['breaking']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        if categories['features']:
            entry += "### ✨ Added\n"
            for commit in categories['features']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        if categories['improvements']:
            entry += "### 🚀 Changed\n"
            for commit in categories['improvements']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        if categories['fixes']:
            entry += "### 🐛 Fixed\n"
            for commit in categories['fixes']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        if categories['security']:
            entry += "### 🔒 Security\n"
            for commit in categories['security']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        if categories['docs']:
            entry += "### 📚 Documentation\n"
            for commit in categories['docs']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        if categories['tests']:
            entry += "### 🧪 Tests\n"
            for commit in categories['tests']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        if categories['chores']:
            entry += "### 🔧 Maintenance\n"
            for commit in categories['chores']:
                entry += f"- {commit['message']} ({commit['hash']})\n"
            entry += "\n"
        
        return entry
    
    def update_changelog(self, version: str, changelog_entry: str):
        """更新 CHANGELOG.md"""
        if not self.changelog_path.exists():
            print("❌ CHANGELOG.md 不存在")
            return
        
        # 讀取現有內容
        with open(self.changelog_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到 [Unreleased] 部分並在其後插入新版本
        unreleased_pattern = r'(## \[Unreleased\].*?\n\n)'
        match = re.search(unreleased_pattern, content, re.DOTALL)
        
        if match:
            # 在 [Unreleased] 後插入新版本
            insert_pos = match.end()
            new_content = content[:insert_pos] + changelog_entry + content[insert_pos:]
        else:
            # 如果找不到 [Unreleased]，在第一個版本前插入
            version_pattern = r'(## \[\d+\.\d+\.\d+\])'
            match = re.search(version_pattern, content)
            if match:
                insert_pos = match.start()
                new_content = content[:insert_pos] + changelog_entry + content[insert_pos:]
            else:
                # 如果沒有任何版本，追加到文件末尾
                new_content = content + "\n" + changelog_entry
        
        # 寫回文件
        with open(self.changelog_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ CHANGELOG.md 已更新")
    
    def create_git_tag(self, version: str):
        """創建 Git 標籤"""
        tag_name = f"v{version}"
        try:
            subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=True)
            print(f"✅ 已創建標籤: {tag_name}")
            return tag_name
        except subprocess.CalledProcessError as e:
            print(f"❌ 創建標籤失敗: {e}")
            return None
    
    def show_status(self):
        """顯示當前狀態"""
        current_version = self.get_current_version()
        latest_tag = self.get_latest_tag()
        
        print(f"📊 版本狀態")
        print(f"當前版本: {current_version}")
        print(f"最新標籤: {latest_tag or 'N/A'}")
        
        # 顯示自最新標籤以來的提交
        commits = self.get_git_commits_since_tag(latest_tag)
        if commits:
            print(f"\n📝 自 {latest_tag or '初始提交'} 以來的變更 ({len(commits)} 個提交):")
            categories = self.categorize_commits(commits)
            for category, commits_list in categories.items():
                if commits_list:
                    print(f"  {category}: {len(commits_list)} 個提交")
        else:
            print("\n✅ 沒有未發布的變更")
    
    def release(self, bump_type: str, dry_run: bool = False):
        """執行發布流程"""
        print(f"🚀 開始發布流程 (bump_type: {bump_type})")
        
        if dry_run:
            print("🔍 這是一次乾跑，不會實際進行任何變更")
        
        # 獲取最新標籤
        latest_tag = self.get_latest_tag()
        
        # 獲取提交記錄
        commits = self.get_git_commits_since_tag(latest_tag)
        if not commits:
            print("❌ 沒有新的提交，無需發布")
            return
        
        # 分類提交
        categories = self.categorize_commits(commits)
        
        if not dry_run:
            # 升級版本
            new_version = self.bump_version(bump_type)
            
            # 生成 changelog
            changelog_entry = self.generate_changelog_entry(new_version, categories)
            
            # 更新 CHANGELOG.md
            self.update_changelog(new_version, changelog_entry)
            
            # 提交變更
            subprocess.run(["git", "add", str(self.pyproject_path), str(self.changelog_path)], check=True)
            subprocess.run(["git", "commit", "-m", f"chore: release version {new_version}"], check=True)
            
            # 創建標籤
            tag_name = self.create_git_tag(new_version)
            
            print(f"\n🎉 發布完成!")
            print(f"新版本: {new_version}")
            print(f"標籤: {tag_name}")
            print(f"\n🚀 下一步:")
            print(f"  git push origin main")
            print(f"  git push origin {tag_name}")
        
        else:
            # 乾跑模式，只顯示將要進行的操作
            print(f"\n📋 將要執行的操作:")
            print(f"  1. 升級版本 ({bump_type})")
            print(f"  2. 更新 CHANGELOG.md")
            print(f"  3. 提交變更")
            print(f"  4. 創建標籤")
            
            # 顯示將要生成的 changelog
            temp_version = "X.X.X"
            changelog_entry = self.generate_changelog_entry(temp_version, categories)
            print(f"\n📝 將要添加的 changelog 條目:")
            print(changelog_entry)


def main():
    parser = argparse.ArgumentParser(description="版本管理工具")
    parser.add_argument("command", choices=["status", "release", "bump"], help="要執行的命令")
    parser.add_argument("--type", choices=["patch", "minor", "major"], default="patch", help="版本升級類型")
    parser.add_argument("--dry-run", action="store_true", help="乾跑模式，不實際執行變更")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    vm = VersionManager(project_root)
    
    if args.command == "status":
        vm.show_status()
    elif args.command == "bump":
        vm.bump_version(args.type)
    elif args.command == "release":
        vm.release(args.type, args.dry_run)


if __name__ == "__main__":
    main()