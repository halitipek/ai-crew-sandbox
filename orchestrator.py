#!/usr/bin/env python3
"""
SimplyECS – AI Orchestrator bootstrap
•  PR açar (varsa kullanır) ▸ #MVP‑1
•  Issue kartını Todo ▸ Dev taşır (Projects V2)
•  Slack ping gönderir
"""

import os, requests, textwrap
from github import Github

# ---------- Ayarlar ----------
REPO_FULL    = "halitipek/ai-crew-sandbox"
ISSUE_NUMBER = 1
BRANCH       = "feature/mvp1_world_skeleton"
SLACK_TEXT   = ":rocket: PR *#{pr}* opened for MVP‑1 → {url}"

TOKEN   = os.environ["GH_PAT"]
SLACK   = os.environ["SLACK_WEBHOOK"]
GH_API  = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

gh   = Github(TOKEN)
repo = gh.get_repo(REPO_FULL)

# ---------- GraphQL yardımcı fonksiyon ----------
def gql(query: str, variables: dict | None = None):
    resp = requests.post(GH_API, headers=HEADERS,
                         json={"query": query, "variables": variables or {}},
                         timeout=30)
    resp.raise_for_status()
    return resp.json()

# ---------- Proje ve alan kimliklerini al ----------
def fetch_project_ids():
    owner, name = REPO_FULL.split("/")

    # 1) Proje ID’si
    q_proj = """
    query($o:String!,$n:String!){
      viewer { projectsV2(first:20){nodes{id title}} }
      repository(owner:$o,name:$n){
        projectsV2(first:20){nodes{id title}}
      }
    }"""
    data = gql(q_proj, {"o": owner, "n": name})["data"]
    nodes = data["viewer"]["projectsV2"]["nodes"] + data["repository"]["projectsV2"]["nodes"]
    proj = next((n for n in nodes if "SimplyECS" in n["title"]), nodes[0])
    project_id = proj["id"]
    print("🔍  Using project:", proj["title"])

    # 2) Status alanı + Dev opsiyonu
    q_field = """
    query($p:ID!){
      node(id:$p){
        ... on ProjectV2 {
          field(name:"Status"){
            ... on ProjectV2SingleSelectField {
              id name
              options { id name }
            }
          }
        }
      }
    }"""
    resp = gql(q_field, {"p": project_id})
    if "errors" in resp:
        print("❌ field query ERROR:", resp["errors"])
        raise SystemExit(1)
    sf = resp["data"]["node"]["field"]
    field_id = sf["id"]
    dev_opt = next(o for o in sf["options"] if o["name"].lower()=="dev")["id"]

    # Kısa ID ise global Node ID’ye yükselt
    if len(dev_opt) < 30:
        conv = gql('query($id:ID!){ node(id:$id){ id }}', {"id": dev_opt})
        dev_opt = conv["data"]["node"]["id"]

    print("🗂️  Status field ID:", field_id[:8], "…  Dev option ID:", dev_opt[:8], "…")
    return project_id, field_id, dev_opt

PROJECT_ID, STATUS_FIELD_ID, DEV_OPTION_ID = fetch_project_ids()

# ---------- Kartı taşı ----------
def move_issue_to_dev(item_id: str):
    mut = """
    mutation($proj:ID!,$item:ID!,$field:ID!,$opt:ID!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$proj itemId:$item fieldId:$field
        value:{ singleSelectOptionId:$opt }})
      { item { id } }}
    """
    gql(mut, {"proj": PROJECT_ID, "item": item_id,
              "field": STATUS_FIELD_ID, "opt": DEV_OPTION_ID})
    print("✅  Moved card to Dev")

# ---------- Ana iş akışı ----------
def main():
    # 1) Branch oluştur
    main_sha = repo.get_branch("main").commit.sha
    try:
        repo.create_git_ref(ref=f"refs/heads/{BRANCH}", sha=main_sha)
        print("🌿  Created branch", BRANCH)
    except Exception:
        print("ℹ️  Branch exists; continue")

    # 2) Boş dosyaları ekle
    for path in ("src/ecs/World.hpp","src/ecs/World.cpp"):
        try:
            repo.get_contents(path, ref=BRANCH)
        except Exception:
            repo.create_file(path, f"feat: add {path}", "", branch=BRANCH)
            print("➕  Added", path)

    # 3) PR aç / varsa yeniden kullan
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

    # 4) Issue’u Dev’e taşı
    issue   = repo.get_issue(ISSUE_NUMBER)
    item_id = getattr(issue, "node_id", issue.raw_data["node_id"])
    move_issue_to_dev(item_id)
    issue.create_comment(f"PR #{pr.number} linked")

    # 5) Slack ping
    requests.post(SLACK, json={"text": SLACK_TEXT.format(pr=pr.number, url=pr.html_url)})

if __name__ == "__main__":
    main()
