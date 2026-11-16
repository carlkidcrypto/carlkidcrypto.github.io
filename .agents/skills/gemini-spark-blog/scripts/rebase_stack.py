#!/usr/bin/env python3
"""
rebase_stack.py
Generic automated rebasing tool for stacked GitHub PR workflows.

Discovers open stacked PRs dynamically via the GitHub CLI (`gh`) instead of
hardcoding branch names or PR numbers, then transplants each stack cleanly onto
`origin/<base>` using `git rebase --onto`.

Usage:
  python3 .agents/skills/gemini-spark-blog/scripts/rebase_stack.py [--push] [--dry-run]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Ensure standard CLI paths are accessible
os.environ["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}"


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
        if res.stdout:
            print(f"STDOUT: {res.stdout}", file=sys.stderr)
        if res.stderr:
            print(f"STDERR: {res.stderr}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout.strip()


def normalize_subject(text):
    """Normalize a commit subject or PR title for comparison."""
    text = re.sub(r"\s*\(#\d+\)\s*$", "", text.strip())
    return re.sub(r"\s+", " ", text).lower()


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


def get_commit_sha(repo_dir, ref):
    """Get commit SHA for a ref, or empty string if missing."""
    return run_cmd(f"git rev-parse --verify {ref}", cwd=repo_dir, check=False)


def is_ancestor(repo_dir, ancestor_ref, descendant_ref):
    """Return True if ancestor_ref is an ancestor of descendant_ref."""
    res = subprocess.run(
        f"git merge-base --is-ancestor {ancestor_ref} {descendant_ref}",
        shell=True,
        cwd=repo_dir,
        capture_output=True,
    )
    return res.returncode == 0


def fetch_open_prs(repo_dir):
    """Fetch open non-fork PRs from GitHub."""
    out = run_cmd(
        "gh pr list --state open --limit 100 "
        "--json number,title,headRefName,baseRefName,headRefOid,isCrossRepository",
        cwd=repo_dir,
    )
    prs = json.loads(out) if out else []
    return [pr for pr in prs if not pr.get("isCrossRepository")]


def fetch_merged_prs(repo_dir, limit=40):
    """Fetch recently merged PRs from GitHub."""
    out = run_cmd(
        f"gh pr list --state merged --limit {limit} "
        "--json number,title,headRefName,headRefOid,mergedAt",
        cwd=repo_dir,
        check=False,
    )
    return json.loads(out) if out else []


def discover_stacks(open_prs, base_branch, root_filter=None):
    """
    Build ordered PR stacks rooted at `base_branch` from open PR metadata.

    Returns a list of stacks, where each stack is an ordered list of PR dicts
    from root -> leaf (topological order).
    """
    by_head = {pr["headRefName"]: pr for pr in open_prs}
    children = defaultdict(list)
    for pr in open_prs:
        children[pr["baseRefName"]].append(pr)

    for base in children:
        children[base].sort(key=lambda p: p["number"])

    # Candidate roots are open PRs targeting `base_branch`
    roots = list(children.get(base_branch, []))
    if root_filter:
        roots = [
            pr
            for pr in open_prs
            if pr["headRefName"] == root_filter or str(pr["number"]) == str(root_filter)
        ]
        if not roots:
            print(
                f"Could not find open PR matching --root '{root_filter}'.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        # Only include root PRs that have downstream stacked children
        # (or are themselves part of a multi-PR chain)
        roots = [pr for pr in roots if children.get(pr["headRefName"])]

    stacks = []
    for root in roots:
        ordered = []
        queue = [root]
        visited = set()
        while queue:
            curr = queue.pop(0)
            head = curr["headRefName"]
            if head in visited:
                continue
            visited.add(head)
            ordered.append(curr)
            for child in children.get(head, []):
                queue.append(child)
        stacks.append(ordered)

    # Also handle orphaned chains whose upstream parent PR was not targeting base_branch
    if not root_filter and not stacks:
        for pr in sorted(open_prs, key=lambda p: p["number"]):
            if pr["baseRefName"] not in by_head and children.get(pr["headRefName"]):
                ordered = []
                queue = [pr]
                visited = set()
                while queue:
                    curr = queue.pop(0)
                    head = curr["headRefName"]
                    if head in visited:
                        continue
                    visited.add(head)
                    ordered.append(curr)
                    for child in children.get(head, []):
                        queue.append(child)
                stacks.append(ordered)

    return stacks


def ensure_local_branch(repo_dir, branch, dry_run=False):
    """Ensure local branch exists and points to origin/<branch>."""
    remote_ref = f"origin/{branch}"
    remote_sha = get_commit_sha(repo_dir, remote_ref)
    if not remote_sha:
        print(f"Remote branch {remote_ref} does not exist.", file=sys.stderr)
        sys.exit(1)

    local_sha = get_commit_sha(repo_dir, f"refs/heads/{branch}")
    if not local_sha:
        if dry_run:
            return remote_sha
        run_cmd(f"git branch {branch} {remote_ref}", cwd=repo_dir)
        return remote_sha

    if local_sha != remote_sha and not dry_run:
        run_cmd(f"git branch -f {branch} {remote_ref}", cwd=repo_dir)
    return remote_sha


def detect_old_root_base(repo_dir, base_ref, root_pr, merged_prs):
    """
    Determine the commit SHA right before root_pr's unique commits so
    `git rebase --onto <base_ref> <old_root_base> <root_branch>` drops
    commits already merged into `<base_ref>` via upstream PRs.
    """
    root_ref = f"origin/{root_pr['headRefName']}"

    # 1. Exact ancestor match against recently merged PR head SHAs
    merged_ancestors = []
    for mpr in merged_prs:
        msha = mpr.get("headRefOid")
        if (
            msha
            and get_commit_sha(repo_dir, msha)
            and is_ancestor(repo_dir, msha, root_ref)
        ):
            merged_ancestors.append(msha)

    if merged_ancestors:
        # Pick the newest ancestor along root_ref
        commits_raw = run_cmd(
            f"git rev-list --reverse {base_ref}..{root_ref}",
            cwd=repo_dir,
            check=False,
        )
        commits = commits_raw.splitlines() if commits_raw else []
        ancestor_set = set(merged_ancestors)
        for sha in reversed(commits):
            if sha in ancestor_set:
                return sha

    # 2. Match commits in base_ref..root_ref against base_ref subjects / merged PR titles
    commits_out = run_cmd(
        f"git log --reverse --format=%H%x09%s {base_ref}..{root_ref}",
        cwd=repo_dir,
        check=False,
    )
    branch_commits = []
    for line in commits_out.splitlines():
        if "\t" in line:
            sha, subj = line.split("\t", 1)
            branch_commits.append((sha, subj))

    if not branch_commits:
        return run_cmd(f"git merge-base {base_ref} {root_ref}", cwd=repo_dir)

    base_subjects_out = run_cmd(
        f"git log -n 60 --format=%s {base_ref}",
        cwd=repo_dir,
        check=False,
    )
    known_merged_titles = {
        normalize_subject(s) for s in base_subjects_out.splitlines() if s.strip()
    }
    for mpr in merged_prs:
        if mpr.get("title"):
            known_merged_titles.add(normalize_subject(mpr["title"]))

    root_title_norm = normalize_subject(root_pr.get("title", ""))

    # Find the last commit index matching a merged PR title
    last_merged_idx = -1
    for idx, (_, subj) in enumerate(branch_commits):
        if normalize_subject(subj) in known_merged_titles:
            last_merged_idx = idx

    # If the root PR's own first commit matches its PR title after `last_merged_idx`,
    # its parent (`first_root_sha^`) is the exact boundary (even if the merged upstream
    # PR had extra fixup commits after its initial feat commit).
    if root_title_norm:
        for idx, (sha, subj) in enumerate(branch_commits):
            if idx > last_merged_idx and normalize_subject(subj) == root_title_norm:
                parent_sha = get_commit_sha(repo_dir, f"{sha}^")
                if parent_sha:
                    return parent_sha

    if last_merged_idx >= 0:
        return branch_commits[last_merged_idx][0]

    # 3. Check `git cherry` for identical patches already in base_ref
    cherry_out = run_cmd(
        f"git cherry {base_ref} {root_ref}",
        cwd=repo_dir,
        check=False,
    )
    last_cherry_merged = None
    for line in cherry_out.splitlines():
        if line.startswith("- "):
            last_cherry_merged = line[2:].strip()
    if last_cherry_merged:
        return last_cherry_merged

    # 4. Fallback to merge-base
    return run_cmd(f"git merge-base {base_ref} {root_ref}", cwd=repo_dir)


def rebase_single_stack(
    repo_dir, stack, base_branch, merged_prs, push=False, dry_run=False, old_base=None
):
    """Execute the `--onto` rebase cascade for one discovered PR stack."""
    base_ref = f"origin/{base_branch}"
    base_sha = get_commit_sha(repo_dir, base_ref)
    root_pr = stack[0]
    root_branch = root_pr["headRefName"]
    root_num = root_pr["number"]

    print(
        f"\nStack root: {root_branch} (PR #{root_num}), total {len(stack)} PR(s) in stack"
    )
    for pr in stack:
        print(
            f"  - PR #{pr['number']}: {pr['headRefName']} (base: {pr['baseRefName']})"
        )

    # Snapshot initial remote/local SHAs before any rebasing
    initial_shas = {}
    for pr in stack:
        branch = pr["headRefName"]
        initial_shas[branch] = ensure_local_branch(repo_dir, branch, dry_run=dry_run)

    # Step 1: Rebase Root Branch onto origin/<base>
    print(f"\n[Step 1] Rebasing root branch {root_branch} onto {base_ref}...")
    root_ref = f"origin/{root_branch}" if dry_run else root_branch
    merge_base = run_cmd(f"git merge-base {base_ref} {root_ref}", cwd=repo_dir)

    if merge_base != base_sha:
        resolved_old_base = old_base or detect_old_root_base(
            repo_dir, base_ref, root_pr, merged_prs
        )
        print(f"  Detected upstream boundary: {resolved_old_base[:12]}")
        if dry_run:
            print(f"  [DRY-RUN] git checkout {root_branch}")
            print(
                f"  [DRY-RUN] git rebase --onto {base_ref} {resolved_old_base} {root_branch}"
            )
        else:
            run_cmd(f"git checkout {root_branch}", cwd=repo_dir)
            run_cmd(
                f"git rebase --onto {base_ref} {resolved_old_base} {root_branch}",
                cwd=repo_dir,
            )
            print(f"  Successfully rebased {root_branch} onto {base_ref}.")
    else:
        print(f"  {root_branch} is already based on {base_ref}.")

    if push and not dry_run and root_pr["baseRefName"] != base_branch:
        print(f"  Updating PR #{root_num} base to {base_branch} via gh CLI...")
        run_cmd(
            f"gh pr edit {root_num} --base {base_branch}", cwd=repo_dir, check=False
        )

    # Step 2: Rebase Downstream Branches Sequentially
    if len(stack) > 1:
        print("\n[Step 2] Rebasing downstream branches in the stack...")
    for i in range(1, len(stack)):
        child_pr = stack[i]
        child_branch = child_pr["headRefName"]
        parent_branch = child_pr["baseRefName"]
        if parent_branch not in initial_shas:
            parent_branch = stack[i - 1]["headRefName"]
        old_parent_sha = initial_shas[parent_branch]

        print(
            f"  Rebasing {child_branch} (PR #{child_pr['number']}) onto {parent_branch} "
            f"(old parent: {old_parent_sha[:8]})..."
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

    # Step 3: Push with --force-with-lease
    if push and not dry_run:
        print(
            "\n[Step 3] Pushing all rebased branches to origin (--force-with-lease)..."
        )
        for pr in stack:
            branch = pr["headRefName"]
            print(f"  Pushing {branch} (PR #{pr['number']})...")
            run_cmd(f"git push --force-with-lease origin {branch}", cwd=repo_dir)
        print("\nAll branches pushed successfully! CI check runs triggered.")
    elif not push:
        print(
            "\nRebase complete locally! To push all rebased branches to remote, re-run with --push."
        )


def rebase_stack(
    repo_dir,
    base_branch="main",
    root_filter=None,
    old_base=None,
    push=False,
    dry_run=False,
):
    """Discover active PR stacks and rebase each one cleanly."""
    check_clean_working_tree(repo_dir)

    print("Fetching origin...")
    run_cmd("git fetch origin --prune", cwd=repo_dir)

    open_prs = fetch_open_prs(repo_dir)
    if not open_prs:
        print("No open PRs found. Nothing to rebase.")
        return

    stacks = discover_stacks(open_prs, base_branch, root_filter=root_filter)
    if not stacks:
        print("No active stacked PR chains found. Nothing to rebase.")
        return

    merged_prs = fetch_merged_prs(repo_dir)
    for stack in stacks:
        rebase_single_stack(
            repo_dir,
            stack,
            base_branch=base_branch,
            merged_prs=merged_prs,
            push=push,
            dry_run=dry_run,
            old_base=old_base,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Generic automated sequential rebase for stacked GitHub PRs."
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Target base branch name (default: main).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Optional root PR number or branch name to rebase a specific stack.",
    )
    parser.add_argument(
        "--old-base",
        default=None,
        help="Optional explicit upstream commit SHA to transplant the root branch from.",
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

    repo_root_out = run_cmd("git rev-parse --show-toplevel", check=False)
    repo_dir = Path(repo_root_out) if repo_root_out else Path.cwd()

    rebase_stack(
        repo_dir,
        base_branch=args.base,
        root_filter=args.root,
        old_base=args.old_base,
        push=args.push,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
