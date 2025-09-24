# Repo Miner

A data-collection pipeline for GitHub commit and issue data.

## Setup

1. Create virtual environment: `python -m venv venv`
2. Activate `source venv/Scripts/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Set GitHub token: `export GITHUB_TOKEN=your_token_here`

## Usage

Fetch commits from a repository:
```bash
python -m src.repo_miner fetch-commits --repo owner/repo --max 100 --out commits.csv