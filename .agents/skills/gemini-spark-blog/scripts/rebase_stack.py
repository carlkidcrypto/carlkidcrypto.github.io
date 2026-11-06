#!/usr/bin/env python3
"""
rebase_stack.py
Automated rebasing and merge scheme for stacked PR workflows.

Solves the classic stacked PR conflict problem where merging an upstream PR
(via GitHub Squash and Merge or Rebase and Merge) orphans downstream branches
because commit SHAs on main differ from the local pre-merge branch commits.

Usage:
  python3 .agents/skills/gemini-spark-blog/scripts/rebase_stack.py [--push] [--dry-run]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Ensure standard CLI paths are accessible
os.environ["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}"

# Canonical sequence of stacked branches and their PR numbers
ORDERED_STACK = [
    ("feature/blog-ezsnmp-working-with-mibs-guide", 19),
    ("feature/blog-ezsnmp-async-polling-event-loops", 20),
    ("feature/blog-ezsnmp-resilient-polling-error-handling", 21),
    ("feature/blog-ezsnmp-advanced-table-navigation", 22),
    ("feature/gemini-spark-blog-skill", 23),
    ("feature/blog-ezsnmp-cpp17-native-architecture", 24),
    ("feature/blog-ezsnmp-custom-observability-exporters", 25),
    ("feature/blog-ezsnmp-network-topology-discovery-lldp-cdp", 26),
    ("feature/blog-ezsnmp-set-operations-device-configuration", 27),
    ("feature/blog-ezsnmp-realtime-telemetry-polars-duckdb", 29),
    ("feature/blog-ezsnmp-vlan-management-qinq-automation", 30),
    ("feature/blog-ezsnmp-custom-agent-extensions-agentx", 31),
    ("feature/blog-ezsnmp-snmpv3-tls-dtls-security", 32),
    ("feature/blog-ezsnmp-hardware-optical-dom-monitoring", 33),
    ("feature/blog-ezsnmp-testing-ci-cd-pytest", 34),
    ("feature/blog-ezsnmp-dynamic-inventory-sync-netbox", 35),
    ("feature/blog-ezsnmp-bgp-routing-telemetry", 36),
    ("feature/blog-ezsnmp-enterprise-poe-power-auditing", 37),
    ("feature/blog-ezsnmp-traffic-flow-netflow-ipfix-auditing", 39),
    ("feature/blog-ezsnmp-ospf-isis-link-state-telemetry", 41),
]


def run_cmd(cmd, cwd=None, check=True):
    """Run shell command and return stdout."""
    res = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if check and res.returncode != 0:
        print(f"Error running: {cmd}", file=sys.stderr)
        print(f"STDOUT: {res.stdout}", file=sys.stderr)
        print(f"STDERR: {res.stderr}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout.strip()


def check_clean_working_tree(repo_dir):
    """Ensure working directory has no uncommitted changes."""
    status = run_cmd("git status --porcelain", cwd=repo_dir)
    if status:
        print(
            "Working directory has uncommitted changes. Please commit or stash before rebasing.",
            file=sys.stderr,
        )
        print(status, file=sys.stderr)
        sys.exit(1)


def is_pr_merged(repo_dir, pr_number):
    """Check if PR is merged using gh CLI or git history."""
    try:
        out = run_cmd(
            f"gh pr view {pr_number} --json state,mergedAt",
            cwd=repo_dir,
            check=False,
        )
        if out:
            s = out.find("{")
            e = out.rfind("}")
            if s != -1 and e != -1:
                data = json.loads(out[s : e + 1])
                return data.get("state") == "MERGED"
    except Exception:
        pass

    # Fallback: check git log on origin/main for (#<pr_number>)
    try:
        log_match = run_cmd(
            f'git log origin/main --grep="(#{pr_number})" -n 1 --oneline',
            cwd=repo_dir,
            check=False,
        )
        if log_match:
            return True
    except Exception:
        pass

    return False


def get_commit_sha(repo_dir, ref):
    """Get commit SHA for a ref."""
    return run_cmd(f"git rev-parse {ref}", cwd=repo_dir, check=False)


def rebase_stack(repo_dir, push=False, dry_run=False):
    """
    Executes the exact mathematical rebase scheme across all stacked branches.
    """
    check_clean_working_tree(repo_dir)

    print("Fetching origin...")
    run_cmd("git fetch origin", cwd=repo_dir)

    # Determine which branches in ORDERED_STACK are already merged into main
    active_stack = []
    last_merged_branch = None
    last_merged_pr = None

    for branch, pr_num in ORDERED_STACK:
        # Check if PR is merged
        if is_pr_merged(repo_dir, pr_num):
            last_merged_branch = branch
            last_merged_pr = pr_num
        else:
            # If gh isn't available, check if commit is already ancestor of origin/main
            active_stack.append((branch, pr_num))

    if not active_stack:
        print("All PRs in the stack appear to be merged! Nothing to rebase.")
        return

    root_branch, root_pr = active_stack[0]
    print(
        f"Active stack has {len(active_stack)} branches. Root branch: {root_branch} (PR #{root_pr})"
    )
    if last_merged_branch:
        print(f"Last merged upstream branch: {last_merged_branch} (PR #{last_merged_pr})")

    # Snapshot initial local commit SHAs of all branches before any rebasing
    initial_shas = {}
    for branch, _ in active_stack:
        initial_shas[branch] = get_commit_sha(repo_dir, branch)
    if last_merged_branch:
        initial_shas[last_merged_branch] = get_commit_sha(
            repo_dir, f"origin/{last_merged_branch}"
        ) or get_commit_sha(repo_dir, last_merged_branch)

    # Step 1: Update local main
    print("\n[Step 1] Fast-forwarding local main to origin/main...")
    if not dry_run:
        run_cmd("git checkout main", cwd=repo_dir)
        run_cmd("git merge --ff-only origin/main", cwd=repo_dir)

    # Step 2: Rebase Root Branch onto main
    print(f"\n[Step 2] Rebasing root branch {root_branch} onto main...")
    merge_base = run_cmd(f"git merge-base main {root_branch}", cwd=repo_dir)
    main_sha = run_cmd("git rev-parse main", cwd=repo_dir)

    if merge_base != main_sha:
        old_root_base = initial_shas.get(last_merged_branch) or run_cmd(
            f"git merge-base origin/main {root_branch}", cwd=repo_dir
        )
        if dry_run:
            print(f"[DRY-RUN] git checkout {root_branch}")
            print(f"[DRY-RUN] git rebase --onto main {old_root_base} {root_branch}")
        else:
            run_cmd(f"git checkout {root_branch}", cwd=repo_dir)
            run_cmd(
                f"git rebase --onto main {old_root_base} {root_branch}",
                cwd=repo_dir,
            )
            print(f"  Successfully rebased {root_branch} onto main.")
    else:
        print(f"  {root_branch} is already based on main.")

    # Ensure PR base is updated to main
    if push and not dry_run and root_pr:
        print(f"  Updating PR #{root_pr} base to main via gh CLI...")
        run_cmd(f"gh pr edit {root_pr} --base main", cwd=repo_dir, check=False)

    # Step 3: Rebase Downstream Branches Sequentially
    print("\n[Step 3] Rebasing downstream branches in the stack...")
    for i in range(1, len(active_stack)):
        child_branch, child_pr = active_stack[i]
        parent_branch, _ = active_stack[i - 1]
        old_parent_sha = initial_shas[parent_branch]

        print(
            f"  Rebasing {child_branch} onto {parent_branch} (old parent: {old_parent_sha[:8]})..."
        )
        if dry_run:
            print(
                f"  [DRY-RUN] git rebase --onto {parent_branch} {old_parent_sha} {child_branch}"
            )
        else:
            run_cmd(f"git checkout {child_branch}", cwd=repo_dir)
            run_cmd(
                f"git rebase --onto {parent_branch} {old_parent_sha} {child_branch}",
                cwd=repo_dir,
            )
            print(f"    Done rebasing {child_branch}.")

    # Step 4: Push to origin with force-with-lease
    if push and not dry_run:
        print("\n[Step 4] Pushing all rebased branches to origin (--force-with-lease)...")
        for branch, pr_num in active_stack:
            print(f"  Pushing {branch} (PR #{pr_num})...")
            run_cmd(f"git push --force-with-lease origin {branch}", cwd=repo_dir)
        print("\nAll branches pushed successfully! CI check runs triggered.")
    elif not push:
        print(
            "\nRebase complete locally! To push all rebased branches to remote, re-run with --push."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Automated sequential rebase for stacked PRs."
    )
    parser.add_argument(
        "--push",
        "-p",
        action="store_true",
        help="Push rebased branches to remote using --force-with-lease and update PR base.",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Simulate the rebasing steps without modifying branches.",
    )
    args = parser.parse_args()

    # Locate repo directory
    script_dir = Path(__file__).resolve().parent
    repo_dir = script_dir.parents[3]  # .agents/skills/gemini-spark-blog/scripts -> repo root
    if not (repo_dir / ".git").is_dir():
        repo_dir = Path.cwd()

    rebase_stack(repo_dir, push=args.push, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
