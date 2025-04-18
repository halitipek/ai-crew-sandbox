#!/usr/bin/env python3
"""
SimplyECS – AI Orchestrator bootstrap
•  PR açar (varsa kullanır) ▸ #MVP‑1
•  Issue kartını Todo ▸ Dev taşır (Projects V2)
•  Slack ping gönderir
"""

import os, requests, textwrap, json # json'ı import etmeyi unutma
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

    # --- DEBUG BAŞLANGIÇ ---
    try:
        # Status Field verisini al ve yazdır
        sf = resp["data"]["node"]["field"]
        print(f"DEBUG: Status Field Data (sf): {json.dumps(sf, indent=2)}") # Gelen tüm Status field verisini gör

        field_id = sf["id"]

        # "Dev" seçeneğini bul ve ID'sini yazdır
        dev_opt_initial = next(o for o in sf["options"] if o["name"].lower()=="dev")["id"]
        print(f"DEBUG: Initial dev_opt ID found: {dev_opt_initial}")

    except (KeyError, TypeError) as e:
        print(f"HATA: API yanıtında beklenen yapı ('data'->'node'->'field') bulunamadı veya 'sf' None geldi. Yanıt: {resp}")
        raise ValueError(f"Status field verisi alınırken yapı hatası: {e}") from e
    except StopIteration:
        print("HATA: 'Status' alanında 'Dev' isimli seçenek bulunamadı!")
        raise ValueError("Status alanında 'Dev' seçeneği bulunamadı.")

    dev_opt = dev_opt_initial # Eğer bulunduysa devam et

    # Kısa ID ise global Node ID’ye yükselt
    if len(dev_opt) < 30:
        print(f"DEBUG: dev_opt ('{dev_opt}') is short, attempting to convert to Global Node ID...")
        conv = gql('query($id:ID!){ node(id:$id){ id }}', {"id": dev_opt})
        # ID çevirme sorgusunun yanıtını yazdır
        print(f"DEBUG: ID Conversion Response (conv): {json.dumps(conv, indent=2)}")

        # Daha güvenli erişim:
        node_data = conv.get("data", {}).get("node") # Önce data, sonra node'u güvenli al
        if node_data and node_data.get("id"): # node_data None değilse VE içinde 'id' anahtarı varsa
            dev_opt = node_data["id"]
            print(f"DEBUG: Successfully converted to Global ID: {dev_opt}")
        else:
            print(f"HATA: Kısa ID '{dev_opt}' global Node ID'ye çevrilemedi. API yanıtı sorunlu veya node bulunamadı.")
            # Programı durdurmak daha güvenli olabilir
            raise ValueError(f"Failed to resolve Node ID for dev option: {dev_opt}. API Response: {conv}")
            # Alternatif: Orijinal ID'yi kullanmayı dene? dev_opt = dev_opt_initial (Ancak bu ID muhtemelen sonraki adımlarda çalışmaz)
    else:
        print(f"DEBUG: dev_opt ('{dev_opt}') is long enough ({len(dev_opt)} chars), assuming it's the Global Node ID.")
    # --- DEBUG BİTİŞ ---

    print("🗂️  Status field ID:", field_id[:8], "…  Dev option ID:", dev_opt[:8], "…")
    return project_id, field_id, dev_opt

# --- Fonksiyon çağrısı ve sonrası aynı ---
try:
    PROJECT_ID, STATUS_FIELD_ID, DEV_OPTION_ID = fetch_project_ids()
except ValueError as e:
    print(f"❌ Kritik Hata: Proje/Alan ID'leri alınamadı. {e}")
    exit(1) # ID'ler olmadan devam edilemez, çıkış yap

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
    except Exception: # Daha spesifik hata yakalamak daha iyi olabilir (örn. GithubException)
        print("ℹ️  Branch exists; continue")

    # 2) Boş dosyaları ekle
    for path in ("src/ecs/World.hpp","src/ecs/World.cpp"):
        try:
            repo.get_contents(path, ref=BRANCH)
        except Exception: # Daha spesifik hata yakalamak daha iyi olabilir
            try:
                repo.create_file(path, f"feat: add {path}", "", branch=BRANCH)
                print("➕  Added", path)
            except Exception as e_create:
                print(f"❌ Error adding file {path}: {e_create}")


    # 3) PR aç / varsa yeniden kullan
    pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{BRANCH}")
    if pulls.totalCount:
        pr = pulls[0]
        print("🔗  PR already exists:", pr.html_url)
    else:
        try:
            pr = repo.create_pull(
                title="feat: MVP‑1 World skeleton",
                body=f"Closes #{ISSUE_NUMBER} – adds empty World class files.", # Issue numarasını değişkenden al
                base="main", head=BRANCH
            )
            print("🔗  PR opened:", pr.html_url)
        except Exception as e_pr:
            print(f"❌ Error creating PR: {e_pr}")
            return # PR açılamazsa devam etme

    # 4) Issue’u Dev’e taşı
    try:
        issue   = repo.get_issue(ISSUE_NUMBER)
        # issue objesinde node_id attribute'u yoksa raw_data'dan almayı dene
        item_id = getattr(issue, "node_id", issue.raw_data.get("node_id"))
        if not item_id:
             print(f"❌ Error: Could not get node_id for issue #{ISSUE_NUMBER}")
             return # item_id olmadan taşıma yapılamaz

        move_issue_to_dev(item_id)
        issue.create_comment(f"PR #{pr.number} linked")
    except Exception as e_move:
        print(f"❌ Error moving issue or commenting: {e_move}")


    # 5) Slack ping
    try:
        requests.post(SLACK, json={"text": SLACK_TEXT.format(pr=pr.number, url=pr.html_url)}, timeout=10)
        print("📢  Sent Slack notification")
    except NameError:
        print("⚠️ Could not send Slack notification (PR object 'pr' not defined - likely PR creation failed)")
    except Exception as e_slack:
        print(f"⚠️ Error sending Slack notification: {e_slack}")


if __name__ == "__main__":
    main()