from typing import cast

import yaml


def load_seed_repos() -> list[str]:
    with open("config/seeds/repos.yaml") as f:
        data = yaml.safe_load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            repos = []
            repos.extend(data.get("repos", []))
            return repos
        return []


def load_queries() -> list[str]:
    with open("config/seeds/queries.yaml") as f:
        data = yaml.safe_load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return cast(list[str], data.get("queries", []))
        return []
