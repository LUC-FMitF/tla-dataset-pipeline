"""Type definitions for TLA dataset pipeline using TypedDict for better type safety."""

from typing import TypedDict


class UploadStats(TypedDict):
    """Statistics from S3 upload operation.

    Attributes:
        total_files: Total files processed
        uploaded_files: Number of files successfully uploaded
        skipped_files: Number of files skipped (already in S3)
        errors: Number of files that failed to upload
        skipped_reasons: List of reasons files were skipped
    """

    total_files: int
    uploaded_files: int
    skipped_files: int
    errors: int
    skipped_reasons: list[str]


class RepoMetadata(TypedDict):
    """Repository metadata discovered from GitHub API.

    Attributes:
        repo: Full repository name (owner/repo)
        html_url: URL to the repository
        default_branch: Default branch name
        sha: Commit SHA of the default branch
        license_spdx: SPDX identifier of the license (if available)
        discovered_at: ISO timestamp when repository was discovered
        query_hits: List of queries that matched this repository
    """

    repo: str
    html_url: str
    default_branch: str
    sha: str
    license_spdx: str | None
    discovered_at: str
    query_hits: list[str]


class RepositoryDiscovery(TypedDict):
    """Discovered repository collection keyed by repository name.

    Maps repository full names to their metadata.
    """

    # This is actually dict[str, RepoMetadata] but TypedDict doesn't support this directly
    # So we use a flexible approach in actual code


class ApiParams(TypedDict, total=False):
    """GitHub API request parameters.

    Attributes:
        q: Search query string
        sort: Sort field (stars, forks, updated)
        order: Sort order (asc, desc)
        per_page: Results per page
        page: Page number
    """

    q: str
    sort: str
    order: str
    per_page: int
    page: int
