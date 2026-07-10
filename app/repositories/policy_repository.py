import datetime
import json
from pathlib import Path
from typing import Any


class PolicyRepository:
    """Repository handling loading and selection of company expense policies."""

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path(__file__).resolve().parent.parent / "config"

    def get_policy_by_version(self, version: str) -> dict[str, Any]:
        """Load policy by version tag (e.g. 'v1', 'v2')."""
        policy_file = self.config_dir / f"policy_{version}.json"
        if not policy_file.exists():
            # Fallback to general company_policy.json if version not found
            fallback_file = self.config_dir.parent / "company_policy.json"
            if fallback_file.exists():
                with open(fallback_file, encoding="utf-8") as f:
                    return json.load(f)
            raise FileNotFoundError(f"Policy file for version '{version}' not found.")

        with open(policy_file, encoding="utf-8") as f:
            return json.load(f)

    def get_policy_by_date(self, date_str: str) -> dict[str, Any]:
        """Find the active policy based on the transaction date (YYYY-MM-DD)."""
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except Exception:
            # Fallback if date is invalid or 'Unknown'
            return self.get_policy_by_version("v1")

        # Scan for policy_v*.json files in config_dir
        version_files = self.config_dir.glob("policy_*.json")
        policies = []
        for file in version_files:
            try:
                with open(file, encoding="utf-8") as f:
                    policy = json.load(f)
                    policies.append(policy)
            except Exception:
                pass

        # Sort by version/effective_date
        policies.sort(key=lambda x: x.get("effective_date", ""))

        # Find matching policy
        for policy in policies:
            eff = datetime.date.fromisoformat(policy["effective_date"])
            exp_str = policy.get("expiration_date")
            exp = datetime.date.fromisoformat(exp_str) if exp_str else None

            if target_date >= eff:
                if exp is None or target_date <= exp:
                    return policy

        # Fallback to the latest policy
        if policies:
            return policies[-1]

        return self.get_policy_by_version("v1")
