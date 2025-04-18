#!/usr/bin/env python3
"""
SimplyECS – AI Orchestrator bootstrap
•  PR açar (varsa kullanır) ▸ #MVP‑1
•  Issue kartını Todo ▸ Dev taşır (Projects V2)
•  Slack ping gönderir
"""

import os, requests, textwrap
from github import Github

# ---------- ayarlar ----------
REPO_FULL     = "halitipek/ai-crew-sandbox"
ISSUE_NUMBER  = 1
BRANCH        = "feature/mvp1_world_skeleton"
SLACK_TEXT    = ":rocket: PR *#{pr}* opened for MVP‑1 → {url}"

TOKEN  = os.environ["GH_PAT"]
SLACK  = os.environ["SLACK_WEBHOOK"]
GH_API = "https://api.github.com/graphql"
HEAD   = {"Authorization": f"Bearer {TOKEN}"}

gh   = Github(TOKEN)
repo = gh.get_repo(REPO_FULL)

# ---------- GraphQL yardımcıları ----------
def gql(query: str, variables: dict | None = None):
    r = requests.post(GH_API, headers=HEAD,
                      json={"query": query, "variables": variables or {}},
                      timeout=30)
    r.raise_for_status()
    return r.json()

# ---------- Proje / Alan / Dev kimlikleri ----------
def fetch_project_ids():
    owner, name = REPO_FULL.split("/")

    q_projects = """
      query($o:String!,$n:String!){
        viewer      { projectsV2(first:20){nodes{id title}} }
        repository(owner:$o,name:$n){ projectsV2(first:20){nodes{id title}} }
      }"""
    data = gql(q_projects, {"o": owner, "n": name})["data"]
    nodes = data["viewer"]["projectsV2"]["nodes"] + \
            data["repository"]["projectsV2"]["nodes"]

    proj = next((n for n in nodes if "SimplyECS" in n["title"]), nodes[0])
    project_id = proj["id"]
    print("🔍  Using project:", proj["title"])

    q_fields = """
      query($p:ID!){ node(id:$p){
        ... on ProjectV2{ fields(first:20){
          nodes{ __typename ... on ProjectV2SingleSelectField{
            id name options{id name} } }}}}
    """
    # önceki q_fields tanımı aynı kalsın
    resp = gql(q_fields, {"p": project_id})
    print("▶️ fields response:", resp)      # tüm JSON’u bas
    if "errors" in resp:
        # eğer hata varsa çıkalım
        print("❌ fields query ERROR:", resp["errors"])
        raise SystemExit(1)

    fields = resp["data"]["node"]["fields"]["nodes"]
    status = next(f for f in fields if f["__typename"] == "ProjectV2SingleSelectField"
                                    and f["name"].lower().startswith("status"))
    field_id = status["id"]

    dev_opt = next(o for o in status["options"]
                   if o["name"].lower() == "dev")["id"]

    # Kısa id'yi (<= 16 hex) global Node ID'ye yükselt
    if len(dev_opt) < 30:
        dev_opt = gql(
          'query($id:ID!){ node(id:$id){ id } }',
          {"id": dev_opt}
        )["data"]["node"]["id"]

    print("🗂️  Status field:", field_id[:10], "… — Dev option:", dev_opt[:10], "…")
    return project_id, field_id, dev_opt

PROJECT_ID, STATUS_FIELD_ID, DEV_OPTION_ID = fetch_project_ids()

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
    # Dal oluştur / varsa geç
    main_sha = repo.get_branch("main").commit.sha
    try:
        repo.create_git_ref(ref=f"refs/heads/{BRANCH}", sha=main_sha)
        print("🌿  Created branch", BRANCH)
    except Exception:
        print("ℹ️  Branch exists; continue")

    # Boş World dosyaları ekle
    for path in ("src/ecs/World.hpp", "src/ecs/World.cpp"):
        try:
            repo.get_contents(path, ref=BRANCH)
        except Exception:
            repo.create_file(path, f"feat: add {path}", "", branch=BRANCH)
            print("➕  Added", path)

    # PR aç / varsa kullan
    pulls = repo.get_pulls(state="open",
                           head=f"{repo.owner.login}:{BRANCH}")
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

    # Issue kartını Dev'e taşı
    issue   = repo.get_issue(ISSUE_NUMBER)
    item_id = getattr(issue, "node_id", issue.raw_data["node_id"])
    move_issue_to_dev(item_id)
    issue.create_comment(f"PR #{pr.number} linked")

    # Slack ping
    requests.post(SLACK, json={
        "text": SLACK_TEXT.format(pr=pr.number, url=pr.html_url)
    })

if __name__ == "__main__":
    main()
