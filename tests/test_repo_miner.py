# tests/test_repo_miner.py

import os
import pandas as pd
import pytest
from datetime import datetime, timedelta
from src.repo_miner import fetch_commits, fetch_issues, merge_and_summarize

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
        self.token = token
    
    def get_repo(self, repo_name):
        if hasattr(self, '_repo'):
            return self._repo
        raise AttributeError("_repo not set on DummyGithub instance")

class DummyUser:
    def __init__(self, login):
        self.login = login

class DummyIssue:
    def __init__(self, id, number, title, user, state,
                 created_at, closed_at, comments,
                 is_pr=False):
        self.id = id
        self.number = number
        self.title = title
        self.user = DummyUser(user) if user else None
        self.state = state
        self.created_at = created_at
        self.closed_at = closed_at
        self.comments = comments
        if is_pr:
            self.pull_request = {"url": "http://example.com/pr"}  
        else:
            self.pull_request = None

class DummyRepoIssues:
    def __init__(self, issues):
        self._issues = issues
    def get_issues(self, state="all"):
        return self._issues

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
    now = datetime.now()
    commits = [
        DummyCommit("sha1", "Unknown Author", "unknown@example.com", now, "Commit with author"),
    ]
    gh_instance._repo = DummyRepo(commits)
    
    df = fetch_commits("any/repo")
    assert len(df) == 1
    assert df.iloc[0]["author"] == "Unknown Author"
    assert df.iloc[0]["email"] == "unknown@example.com"

def test_fetch_issues_excludes_prs(monkeypatch):
    now = datetime.now()
    issues = [
        DummyIssue(1, 101, "Real issue", "alice", "open", now, None, 2, is_pr=False),
        DummyIssue(2, 102, "Pull request disguised", "bob", "open", now, None, 3, is_pr=True),
    ]
    gh_instance._repo = DummyRepoIssues(issues)

    df = fetch_issues("any/repo", state="all")
    assert len(df) == 1
    assert df.iloc[0]["title"] == "Real issue"

def test_fetch_issues_dates_are_iso(monkeypatch):
    now = datetime(2025, 9, 25, 15, 30, 0)
    issues = [
        DummyIssue(1, 201, "Date test", "charlie", "closed", now, now, 0),
    ]
    gh_instance._repo = DummyRepoIssues(issues)

    df = fetch_issues("any/repo", state="all")
    created_at = df.iloc[0]["created_at"]
    closed_at = df.iloc[0]["closed_at"]
    assert created_at.startswith("2025-09-25T15:30:00")
    assert closed_at.startswith("2025-09-25T15:30:00")

def test_fetch_issues_open_duration_days(monkeypatch):
    created = datetime(2025, 1, 1, 12, 0, 0)
    closed = created + timedelta(days=5, hours=3)
    issues = [
        DummyIssue(1, 301, "Duration test", "dana", "closed", created, closed, 1),
    ]
    gh_instance._repo = DummyRepoIssues(issues)

    df = fetch_issues("any/repo", state="all")
    assert df.iloc[0]["open_duration_days"] == 5

def test_merge_and_summarize_output(capsys):
    # Prepare test DataFrames
    df_commits = pd.DataFrame({
        "sha": ["a", "b", "c", "d"],
        "author": ["X", "Y", "X", "Z"],
        "email": ["x@e", "y@e", "x@e", "z@e"],
        "date": ["2025-01-01T00:00:00", "2025-01-01T01:00:00",
                 "2025-01-02T00:00:00", "2025-01-02T01:00:00"],
        "message": ["m1", "m2", "m3", "m4"]
    })
    df_issues = pd.DataFrame({
        "id": [1,2,3],
        "number": [101,102,103],
        "title": ["I1","I2","I3"],
        "user": ["u1","u2","u3"],
        "state": ["closed","open","closed"],
        "created_at": ["2025-01-01T00:00:00","2025-01-01T02:00:00","2025-01-02T00:00:00"],
        "closed_at": ["2025-01-01T12:00:00",None,"2025-01-02T12:00:00"],
        "comments": [0,1,2]
    })
    # Run summarize
    merge_and_summarize(df_commits, df_issues)
    captured = capsys.readouterr().out
    # Check top committer
    assert "Top 5 Committers" in captured
    assert "X: 2 commits" in captured
    # Check close rate
    assert "Issue Close Rate: 67.0%" in captured
    # Check avg open duration
    assert "Average Open Duration for Closed Issues:" in captured
