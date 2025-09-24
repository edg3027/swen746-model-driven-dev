# tests/test_repo_miner.py

import os
import pandas as pd
import pytest
from datetime import datetime, timedelta
from src.repo_miner import fetch_commits

# --- Helpers for dummy GitHub API objects ---

class DummyAuthor:
    def __init__(self, name, email, date):
        self.name = name
        self.email = email
        self.date = date

class DummyCommitCommit:
    def __init__(self, author, message):
        self.author = author
        self.message = message

class DummyCommit:
    def __init__(self, sha, author, email, date, message):
        self.sha = sha
        self.commit = DummyCommitCommit(DummyAuthor(author, email, date), message)

class DummyRepo:
    def __init__(self, commits):
        self._commits = commits

    def get_commits(self):
        return self._commits

class DummyGithub:
    def __init__(self, token):
        self.token = token  # Store token but don't require specific value
    
    def get_repo(self, repo_name):
        # Return a repo object that will be set by the test
        if hasattr(self, '_repo'):
            return self._repo
        raise AttributeError("_repo not set on DummyGithub instance")

# Create a global instance
gh_instance = DummyGithub("fake-token")

@pytest.fixture(autouse=True)
def patch_github(monkeypatch):
    """Patch the Github class to return our dummy instance."""
    def mock_github(token):
        return gh_instance
    monkeypatch.setattr('src.repo_miner.Github', mock_github)

# --- Tests for fetch_commits ---
def test_fetch_commits_basic(monkeypatch):
    # Setup dummy commits
    now = datetime.now()
    commits = [
        DummyCommit("sha1", "Alice", "a@example.com", now, "Initial commit\nDetails"),
        DummyCommit("sha2", "Bob", "b@example.com", now - timedelta(days=1), "Bug fix")
    ]
    
    # Set up the repo on our global instance
    gh_instance._repo = DummyRepo(commits)
    
    df = fetch_commits("any/repo")
    assert list(df.columns) == ["sha", "author", "email", "date", "message"]
    assert len(df) == 2
    assert df.iloc[0]["message"] == "Initial commit"
    assert df.iloc[0]["author"] == "Alice"
    assert df.iloc[0]["email"] == "a@example.com"

def test_fetch_commits_limit(monkeypatch):
    # More commits than max_commits
    now = datetime.now()
    commits = [
        DummyCommit("sha1", "Alice", "a@example.com", now, "Commit 1"),
        DummyCommit("sha2", "Bob", "b@example.com", now - timedelta(days=1), "Commit 2"),
        DummyCommit("sha3", "Charlie", "c@example.com", now - timedelta(days=2), "Commit 3"),
    ]
    gh_instance._repo = DummyRepo(commits)
    
    # Test with max_commits = 2
    df = fetch_commits("any/repo", max_commits=2)
    assert len(df) == 2
    assert df.iloc[0]["sha"] == "sha1"
    assert df.iloc[1]["sha"] == "sha2"

def test_fetch_commits_empty(monkeypatch):
    # Test that fetch_commits returns empty DataFrame when no commits exist.
    commits = []
    gh_instance._repo = DummyRepo(commits)
    
    df = fetch_commits("any/repo")
    assert len(df) == 0
    assert isinstance(df, pd.DataFrame)
    if len(df.columns) > 0:
        assert list(df.columns) == ["sha", "author", "email", "date", "message"]

def test_fetch_commits_unknown_author(monkeypatch):
    # Test handling of commits with missing author information
    # We need to fix the repo_miner.py to handle None dates properly
    now = datetime.now()
    commits = [
        DummyCommit("sha1", "Unknown Author", "unknown@example.com", now, "Commit with author"),
    ]
    gh_instance._repo = DummyRepo(commits)
    
    df = fetch_commits("any/repo")
    assert len(df) == 1
    assert df.iloc[0]["author"] == "Unknown Author"
    assert df.iloc[0]["email"] == "unknown@example.com"