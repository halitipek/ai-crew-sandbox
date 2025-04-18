#!/usr/bin/env python3
"""
SimplyECS – AI Orchestrator bootstrap
•  Opens a feature branch + PR for MVP‑1
•  Moves its issue card from Todo → Dev (Projects V2)
•  Sends a Slack ping
"""

import os, base64, requests, textwrap
from github import Github

# ------------------------  CONFIG  ------------------------
REPO_FULL = "halitipek/ai-crew-sandbox"   # owner/repo
ISSUE_NUMBER = 1                          # MVP‑1 issue no.
BRANCH = "feature/mvp1_world_skeleton"
SLACK_TEXT = ":rocket: PR *#{pr}* opened for MVP‑1 → {url}"

TOKEN  = os.environ["GH_PAT"]
SLACK  = os.environ["SLACK_WEBHOOK"]
GH_API = "https://api.github.com/graphql"
HEAD   = {"Authorization": f"Bearer {TOKEN}"}

# --------------------  GITHUB HELPERS  --------------------
gh = Github(TOKEN)
repo = gh.get_repo(REPO_FULL)

def gql(query: str, variables: dict = None):
    r = requests.post(GH_API, json={"query": query, "variables": variables or {}},
                      headers=HEAD, timeout=30)
    r.raise_for_status()
    return r.json()

# --------------------  PROJECT ID LOOKUP  -----------------
def fetch_project_ids():
    q = textwrap.dedent("""
      query($owner:String!,$name:String!){
        viewer { projectsV2(first:20){nodes{id title}} }
        repository(owner:$owner, name:$name){
          projectsV2(first:20){nodes{id title}} }
      }""")
    data = gql(q, {"owner": REPO_FULL.split("/")[0],
                   "name":  REPO_FULL.split("/")[1]})["data"]
    nodes = data["viewer"]["projectsV2"]["nodes"] + \
            data["repository"]["projectsV2"]["nodes"]

    # Tolerant match: any title containing "SimplyECS"
    proj = next((n for n in nodes if "SimplyECS" in n["title"]), nodes[0])
    project_id = proj["id"]
    print("🔍  Using project:", proj["title"])

    # Status field ID
    q2 = """
      query($p:ID!){ node(id:$p){
        ... on ProjectV2 { field(name:"Status"){ id } } } }
    """
    field_id = gql(q2, {"p": project_id})["data"]["node"]["field"]["id"]

    # 'Dev' option ID
    q3 = """
      query($f:ID!){ node(id:$f){
        ... on ProjectV2SingleSelectField { options{id name} } } }
    """
    opts = gql(q3, {"f": field_id})["data"]["node"]["options"]
    dev_opt = next(o for o in opts if o["name"].lower() == "dev")["id"]

    return project_id, field_id, dev_opt

PROJECT_ID, STATUS_FIELD_ID, DEV_OPTION_ID = fetch_project_ids()

def move_issue_to_dev(item_id: str):
    mut = """
      mutation($proj:ID!,$item:ID!,$field:ID!,$opt:ID!){
        updateProjectV2ItemFieldValue(input:{
          projectId:$proj itemId:$item fieldId:$field
          value:{ singleSelectOptionId:$opt }})
        { item { id } } }
    """
    gql(mut, {"proj": PROJECT_ID, "item": item_id,
              "field": STATUS_FIELD_ID, "opt": DEV_OPTION_ID})
    print("✅  Moved card to Dev")

# --------------------  MAIN WORKFLOW  ---------------------
def main():
    # 1) Create branch
    main_sha = repo.get_branch("main").commit.sha
    try:
        repo.create_git_ref(ref=f"refs/heads/{BRANCH}", sha=main_sha)
        print("🌿  Created branch", BRANCH)
    except Exception:
        print("ℹ️  Branch exists; continue")

    # 2) Add empty files if absent
    for path in ("src/ecs/World.hpp", "src/ecs/World.cpp"):
        try:
            repo.get_contents(path, ref=BRANCH)
        except Exception:
            repo.create_file(path, f"feat: add {path}", "", branch=BRANCH)
            print("➕  Added", path)

    # 3) Open PR (idempotent: returns existing if same head)
    pr = repo.create_pull(
        title="feat: MVP‑1 World skeleton",
        body="Closes #1 – adds empty World class files.",
        base="main", head=BRANCH
    )
    print("🔗  PR opened:", pr.html_url)

    # 4) Link issue & move card
    issue = repo.get_issue(ISSUE_NUMBER)
    issue.create_comment(f"PR #{pr.number} opened for MVP‑1")
    move_issue_to_dev(issue.node_id)

    # 5) Slack ping
    requests.post(SLACK, json={"text": SLACK_TEXT.format(pr=pr.number, url=pr.html_url)})

if __name__ == "__main__":
    main()
