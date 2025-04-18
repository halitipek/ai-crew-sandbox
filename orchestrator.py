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

def gql(query: str, variables: dict | None = None):
    resp = requests.post(
        GH_API,
        headers=HEAD,
        json={"query": query, "variables": variables or {}},
        timeout=30
    )

    # 🔍 DEBUG satırları
    print("▶️  gql HTTP:", resp.status_code)
    print("▶️  gql body:", resp.text[:500].replace("\n", " ")[:500])

    resp.raise_for_status()
    return resp.json()



# --------------------  PROJECT ID LOOKUP  -----------------
def fetch_project_ids() -> tuple[str, str, str]:
    """Return (project_id, status_field_id, dev_option_id)."""

    # -------- 1) Proje (tahta) kimliğini bul --------
    q_proj = """
      query($owner:String!, $name:String!){
        viewer {
          projectsV2(first:20) { nodes { id title } }
        }
        repository(owner:$owner, name:$name){
          projectsV2(first:20) { nodes { id title } }
        }
      }"""

    owner, name = REPO_FULL.split("/")
    data = gql(q_proj, {"owner": owner, "name": name})["data"]
    nodes = data["viewer"]["projectsV2"]["nodes"] + data["repository"]["projectsV2"]["nodes"]

    # Başlığında 'SimplyECS' geçen ilk projeyi al, yoksa dizinin ilkini kullan
    proj = next((n for n in nodes if "SimplyECS" in n["title"]), nodes[0])
    project_id = proj["id"]
    print("🔍  Using project:", proj["title"])

    # -------- 2) Status alanı + Dev opsiyonu --------
    q_fields = """
      query($p:ID!){
        node(id:$p){
          ... on ProjectV2 {
            fields(first:20){
              nodes{
                __typename
                ... on ProjectV2SingleSelectField {
                  id name
                  options { id name }
                }
              }
            }
          }
        }
      }"""

    fields = gql(q_fields, {"p": project_id})["data"]["node"]["fields"]["nodes"]

    status_field = next(
        f for f in fields
        if f.get("__typename") == "ProjectV2SingleSelectField"
        and f["name"].lower().startswith("status")
    )
    field_id = status_field["id"]

    dev_opt = next(
        o for o in status_field["options"]
        if o["name"].lower() == "dev"
    )["id"]

    # Eğer id kısa (< 32 char) ise Node ID'yi sorgula
    if len(dev_opt) < 30:
        q_opt = """
        query($p:ID!){ node(id:$p){
            ... on ProjectV2SingleSelectFieldOption { id } } }
        """
        dev_opt = gql(q_opt, {"p": dev_opt})["data"]["node"]["id"]


    print("🗂️  Status field ID:", field_id[:8], "… — Dev option ID:", dev_opt[:8], "…")
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

    # 3) Open (or reuse) PR
    pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{BRANCH}")
    if pulls.totalCount:
        pr = pulls[0]
        print("🔗  PR already exists:", pr.html_url)
    else:
        pr = repo.create_pull(
            title="feat: MVP‑1 World skeleton",
            body="Closes #1 – adds empty World class files.",
            base="main", head=BRANCH
        )
        print("🔗  PR opened:", pr.html_url)

    # 4) Link issue & move card
    issue = repo.get_issue(ISSUE_NUMBER)
    item_id = getattr(issue, "node_id", issue.raw_data["node_id"])
    move_issue_to_dev(item_id)

    # 5) Slack ping
    requests.post(SLACK, json={"text": SLACK_TEXT.format(pr=pr.number, url=pr.html_url)})

if __name__ == "__main__":
    main()
