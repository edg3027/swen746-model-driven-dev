#!/usr/bin/env python3
"""
repo_miner.py

A command-line tool to:
  1) Fetch and normalize commit data from GitHub

Sub-commands:
  - fetch-commits
"""

import os
import argparse
import pandas as pd
from github import Github

def fetch_commits(repo_name: str, max_commits: int = None) -> pd.DataFrame:
    """
    Fetch up to `max_commits` from the specified GitHub repository.
    Returns a DataFrame with columns: sha, author, email, date, message.
    """
    # 1) Read GitHub token from environment
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    # 2) Initialize GitHub client and get the repo
    g = Github(token)
    repo = g.get_repo(repo_name)

    # 3) Fetch commit objects (paginated by PyGitHub)
    commits_data = []
    commit_count = 0
    
    for commit in repo.get_commits():
        if max_commits and commit_count >= max_commits:
            break

        # 4) Normalize each commit into a record dict
        commit_data = {
            'sha': commit.sha,
            'author': commit.commit.author.name if commit.commit.author else "Unknown",
            'email': commit.commit.author.email if commit.commit.author else "Unknown",
            'date': commit.commit.author.date.isoformat() if commit.commit.author else "Unknown",
            'message': commit.commit.message.split('\n')[0] if commit.commit.message else "No message"
        }
        
        commits_data.append(commit_data)
        commit_count += 1

    # 5) Build DataFrame from records
    df = pd.DataFrame(commits_data)
    return df
    

def main():
    """
    Parse command-line arguments and dispatch to sub-commands.
    """
    parser = argparse.ArgumentParser(
        prog="repo_miner",
        description="Fetch GitHub commits/issues and summarize them"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sub-command: fetch-commits
    c1 = subparsers.add_parser("fetch-commits", help="Fetch commits and save to CSV")
    c1.add_argument("--repo", required=True, help="Repository in owner/repo format")
    c1.add_argument("--max",  type=int, dest="max_commits",
                    help="Max number of commits to fetch")
    c1.add_argument("--out",  required=True, help="Path to output commits CSV")

    args = parser.parse_args()

    # Dispatch based on selected command
    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max_commits)
        df.to_csv(args.out, index=False)
        print(f"Saved {len(df)} commits to {args.out}")

if __name__ == "__main__":
    main()
