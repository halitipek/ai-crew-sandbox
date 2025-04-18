#!/usr/bin/env python3
"""
Very‑small bootstrap: moves MVP‑1 card to Dev, creates feature branch,
adds empty World.hpp/cpp and opens a Pull Request, then pings Slack.
Requires: PyGithub 2.x, requests.
"""

import os, requests, base64
from github import Github

REPO = "halitipek/ai-crew-sandbox"
ISSUE_NUMBER = 1              # MVP‑1
BRANCH = "feature/mvp1_world_skeleton"

gh = Github(os.environ["GH_PAT"])
repo = gh.get_repo(REPO)

# 1) Create branch from main
main_sha = repo.get_branch("main").commit.sha
repo.create_git_ref(ref=f"refs/heads/{BRANCH}", sha=main_sha)

# 2) Add empty files
def add(path):
    repo.create_file(
        path, f"feat: add {path}", "", branch=BRANCH
    )
add("src/ecs/World.hpp")
add("src/ecs/World.cpp")

# 3) Open PR
pr = repo.create_pull(
    title="feat: MVP‑1 World skeleton",
    body="Closes #1 – adds empty World class files.",
    base="main", head=BRANCH,
)

# 4) Link issue & move project card to Dev
issue = repo.get_issue(number=ISSUE_NUMBER)
issue.create_comment(f"Opened PR #{pr.number}")
issue.edit(state="open")              # ensure open
project = repo.get_projects()[0]      # SimplyECS Kanban
column = next(c for c in project.get_columns() if c.name == "Dev")
card = next(card for card in column.get_cards() if card.get_content() and card.get_content().number == ISSUE_NUMBER) \
       if False else project.create_card(content_id=issue.id, content_type="Issue")
card.move("top", column.id)

# 5) Slack ping
requests.post(
    os.environ["SLACK_WEBHOOK"],
    json={"text": f":rocket: PR *#{pr.number}* opened for MVP‑1 <{pr.html_url}|view>"}
)

print("✅ Done!")
