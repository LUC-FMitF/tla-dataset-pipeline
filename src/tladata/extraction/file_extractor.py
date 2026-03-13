"""File extraction from TLA+ repositories."""

import json
from collections.abc import Generator
from pathlib import Path

import requests

from tladata.discovery.github_client import GithubClient
from tladata.utils.load_limits import load_limits


class FileExtractor:
    """Extract .tla, .cfg, and .tlaps files from discovered repositories."""

    TLA_EXTENSIONS = {".tla", ".cfg", ".tlaps"}

    def __init__(self, client: GithubClient):
        self.client = client
        limits = load_limits()
        self.file_download_timeout = limits.get("extraction", "file_download_timeout", 30)
        self.max_file_size = limits.get("extraction", "max_file_size", 10485760)  # 10 MB
        self.max_files_per_repo = limits.get("extraction", "max_files_per_repo", 1000)

    def extract_files(self, manifest_path: str, output_dir: str) -> None:
        """
        Extract TLA files from repositories in manifest and save to output_dir.

        Args:
            manifest_path: Path to discovery manifest JSONL file
            output_dir: Directory to save extracted files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        total_repos = 0
        repos_processed = 0
        total_files = 0

        with open(manifest_path) as f:
            for line in f:
                record = json.loads(line.strip())
                repo = record.get("repo")
                default_branch = record.get("default_branch")
                sha = record.get("sha")

                if not all([repo, default_branch, sha]):
                    print(f"Skipping {repo}: missing required fields")
                    continue

                total_repos += 1
                repos_processed += 1
                print(f"\n[{repos_processed}] Extracting files from {repo}...")
                files_before = self._count_files(output_path)
                self._extract_from_repo(repo, sha, output_path)
                files_after = self._count_files(output_path)
                total_files += (files_after - files_before)
                print(f"[{repos_processed}] Completed {repo} (extracted {files_after - files_before} files)")
        
        print(f"\n✓ Extraction complete: {total_files} files extracted from {repos_processed} repositories")

    def _count_files(self, path: Path) -> int:
        """Count total files in directory tree."""
        return sum(1 for _ in path.rglob('*') if _.is_file())

    def _extract_from_repo(self, repo: str, sha: str, output_base: Path) -> None:
        """Extract TLA files from a single repository."""
        repo_dir = output_base / repo
        repo_dir.mkdir(parents=True, exist_ok=True)

        try:
            file_count = 0
            for file_path in self._find_tla_files(repo, sha):
                if file_count >= self.max_files_per_repo:
                    print(f"  Reached max files limit ({self.max_files_per_repo}) for {repo}")
                    break
                self._download_file(repo, sha, file_path, repo_dir)
                file_count += 1
        except Exception as e:
            print(f"Error extracting from {repo}: {e}")

    def _find_tla_files(self, repo: str, sha: str) -> Generator[str, None, None]:
        """Find all TLA+ files in repository at given commit."""
        url = f"/repos/{repo}/git/trees/{sha}?recursive=1"
        
        print(f"  Querying GitHub API for tree structure of {repo}@{sha[:8]}...")
        try:
            # Use longer timeout for tree queries (they can be slow for large repos)
            tree_data = self.client.get(url, timeout=60)
        except Exception as e:
            print(f"  Failed to query tree for {repo}: {e}")
            print(f"  Skipping {repo} (tree too large or API error)")
            return
            
        tree_items = tree_data.get("tree", [])
        print(f"  Found {len(tree_items)} items in tree, filtering for TLA+ files...")
        
        tla_count = 0
        for item in tree_items:
            if item["type"] == "blob":
                path = item["path"]
                if any(path.endswith(ext) for ext in self.TLA_EXTENSIONS):
                    tla_count += 1
                    yield path
        
        if tla_count == 0:
            print(f"  No TLA+ files found")

    def _download_file(self, repo: str, sha: str, file_path: str, dest_dir: Path) -> None:
        """Download a single file from repository."""
        url = f"https://raw.githubusercontent.com/{repo}/{sha}/{file_path}"

        try:
            response = requests.get(url, timeout=self.file_download_timeout)
            if response.status_code != 200:
                raise Exception(f"Failed to download {file_path}: {response.status_code}")

            # Check file size limit
            if len(response.content) > self.max_file_size:
                print(
                    f"  Skipped {file_path}: exceeds size limit ({len(response.content)} > {self.max_file_size})"
                )
                return

            dest_file = dest_dir / file_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            dest_file.write_text(response.text, encoding="utf-8")
            print(f"  Downloaded: {file_path}")
        except requests.exceptions.Timeout:
            print(f"  Skipped {file_path}: download timeout (>{self.file_download_timeout}s)")
        except Exception as e:
            print(f"  Error downloading {file_path}: {e}")
