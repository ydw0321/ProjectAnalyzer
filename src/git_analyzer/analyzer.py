from git import Repo
import os
import logging


logger = logging.getLogger(__name__)


class GitAnalyzer:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.has_git = True
        try:
            self.repo = Repo(repo_path)
        except Exception as e:
            self.has_git = False
            logger.warning("路径 '%s' 不是有效的 Git 仓库: %s", repo_path, e)

    def get_file_last_commit(self, file_path: str) -> dict:
        if not self.has_git:
            return {"author": "Unknown", "message": "No Git", "date": "Unknown"}

        try:
            relative_path = os.path.relpath(file_path, self.repo_path)
            commits = self.repo.iter_commits(paths=relative_path, max_count=1)
            commit = next(commits, None)

            if commit is None:
                return {"author": "Unknown", "message": "No commit", "date": "Unknown"}

            return {
                "author": commit.author.name,
                "message": commit.message.strip(),
                "date": commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.warning("获取文件最后提交信息失败: file=%s, error=%s", file_path, e)
            return {"author": "Unknown", "message": "Unknown", "date": "Unknown"}
