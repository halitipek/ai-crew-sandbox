#!/usr/bin/env python3
"""
SimplyECS – AI Orchestrator bootstrap
•  PR açar (varsa kullanır) ▸ #MVP‑1
•  Issue kartını Todo ▸ Dev taşır (Projects V2)
•  Slack ping gönderir
"""

import os, requests, textwrap, json
from github import Github, GithubException

# ---------- Ayarlar ----------
REPO_FULL    = "halitipek/ai-crew-sandbox"
ISSUE_NUMBER = 1
BRANCH       = "feature/mvp1_world_skeleton"
SLACK_TEXT   = ":rocket: PR *#{pr}* opened for MVP‑1 → {url}"

TOKEN   = os.environ.get("GH_PAT")
SLACK   = os.environ.get("SLACK_WEBHOOK")

if not TOKEN:
    print("❌ Hata: GH_PAT ortam değişkeni ayarlanmamış.")
    exit(1)
if not SLACK:
    print("❌ Hata: SLACK_WEBHOOK ortam değişkeni ayarlanmamış.")
    exit(1)

GH_API  = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {TOKEN}"} # X-Github-Next-Global-ID başlığı kaldırıldı

gh   = Github(TOKEN)
repo = gh.get_repo(REPO_FULL)

# ---------- GraphQL yardımcı fonksiyon ----------
def gql(query: str, variables: dict | None = None):
    """GraphQL sorgusu gönderir ve yanıtı JSON olarak döndürür veya hata durumunda None."""
    try:
        resp = requests.post(GH_API, headers=HEADERS,
                             json={"query": query, "variables": variables or {}},
                             timeout=30)
        resp.raise_for_status()
        json_resp = resp.json()
        if "errors" in json_resp:
            print(f"❌ GraphQL Query Error: {json.dumps(json_resp['errors'], indent=2)}")
            return None
        if "data" not in json_resp or not json_resp["data"]:
             # Sorgu başarılı olsa bile veri yoksa veya null ise None döndür
             # print(f"ℹ️ GraphQL query successful but returned no data or null data: {json_resp}")
             return None
        return json_resp
    except requests.exceptions.Timeout:
        print("❌ HTTP Request Error: Timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Request Error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error: {e} - Response text starts with: {resp.text[:200]}")
        return None

# ---------- Proje ve alan kimliklerini al ----------
def fetch_project_and_status_info():
    """Proje ID'sini, Status alanını ve 'Dev' seçeneğini alır."""
    owner, name = REPO_FULL.split("/")

    # 1) Proje ID'si
    q_proj = """
    query($o:String!,$n:String!){
      viewer { projectsV2(first:20){nodes{id title}} }
      repository(owner:$o,name:$n){
        projectsV2(first:20){nodes{id title}}
      }
    }"""
    proj_resp = gql(q_proj, {"o": owner, "n": name})
    if not proj_resp: raise ValueError("Proje ID'si sorgusu başarısız.")
    data = proj_resp["data"]
    viewer_nodes = data.get("viewer", {}).get("projectsV2", {}).get("nodes", []) or []
    repo_nodes = data.get("repository", {}).get("projectsV2", {}).get("nodes", []) or []
    nodes = viewer_nodes + repo_nodes
    if not nodes: raise ValueError(f"'{REPO_FULL}' için hiç GitHub Projesi bulunamadı.")
    proj = next((n for n in nodes if n and "SimplyECS" in n.get("title", "")), None)
    if not proj: raise ValueError("'SimplyECS' içeren bir proje bulunamadı.")
    project_id = proj["id"]
    print("🔍  Using project:", proj["title"])

    # 2) Status Alanı ve Seçenekleri Tek Sorguda Al
    q_field_options = """
    query($p:ID!){
      node(id:$p){
        ... on ProjectV2 {
          field(name:"Status"){
            ... on ProjectV2SingleSelectField {
              id
              name
              options {
                id
                name
              }
            }
          }
        }
      }
    }"""
    
    field_resp = gql(q_field_options, {"p": project_id})
    if not field_resp: raise ValueError("Status alanı sorgusu başarısız.")
    
    try:
        field_data = field_resp.get("data", {}).get("node", {}).get("field", {})
        if not field_data: 
            raise ValueError("Status alanı bulunamadı.")
        
        status_field_id = field_data.get("id")
        if not status_field_id:
            raise ValueError("Status alanı ID'si bulunamadı.")
        
        # Seçenekleri doğrudan alıyoruz
        options = field_data.get("options", [])
        if not options:
            raise ValueError("Status alanı seçenekleri bulunamadı.")
        
        # "Dev" seçeneğini bul
        dev_option = next((opt for opt in options if opt.get("name") == "Dev"), None)
        if not dev_option:
            raise ValueError(f"'Dev' seçeneği bulunamadı. Mevcut seçenekler: {[opt.get('name') for opt in options]}")
        
        dev_option_id = dev_option.get("id")
        if not dev_option_id:
            raise ValueError("'Dev' seçeneğinin ID'si bulunamadı.")
        
        print(f"DEBUG: Status field options: {json.dumps(options, indent=2)}")
        print(f"DEBUG: Using Status Field ID: {status_field_id}")
        print(f"DEBUG: Using Dev option ID: {dev_option_id}")
        
        return project_id, status_field_id, dev_option_id
        
    except Exception as e:
        raise ValueError(f"Status alanı bilgileri alınırken hata: {str(e)}")

# ---------- Issue'yu Proje Kartına Dönüştür ve Taşı ----------
def move_issue_card_to_dev(issue_number, project_id, status_field_id, dev_option_id):
    """Issue'yu projeye ekler ve Dev statüsüne taşır."""
    
    # 1. Adım: Issue'nun içerik ID'sini al (GitHub node ID)
    issue_query = """
    query($owner:String!, $repo:String!, $issue:Int!) {
      repository(owner:$owner, name:$repo) {
        issue(number:$issue) {
          id
        }
      }
    }
    """
    
    owner, repo_name = REPO_FULL.split("/")
    issue_resp = gql(issue_query, {"owner": owner, "repo": repo_name, "issue": issue_number})
    
    if not issue_resp:
        print(f"❌ Issue #{issue_number} için ID alınamadı.")
        return False
    
    try:
        issue_id = issue_resp.get("data", {}).get("repository", {}).get("issue", {}).get("id")
        if not issue_id:
            print(f"❌ Issue #{issue_number} için ID bulunamadı.")
            return False
            
        print(f"DEBUG: Issue #{issue_number} ID: {issue_id}")
        
        # 2. Adım: Issue'yu projeye ekle (zaten ekliyse sorun değil)
        add_issue_mutation = """
        mutation($project:ID!, $content:ID!) {
          addProjectV2ItemById(input: {
            projectId: $project,
            contentId: $content
          }) {
            item {
              id
            }
          }
        }
        """
        
        add_resp = gql(add_issue_mutation, {"project": project_id, "content": issue_id})
        
        # Item ID'yi al
        project_item_id = None
        if add_resp and add_resp.get("data", {}).get("addProjectV2ItemById", {}).get("item", {}).get("id"):
            project_item_id = add_resp["data"]["addProjectV2ItemById"]["item"]["id"]
            print(f"DEBUG: Issue added to project, got ProjectV2Item ID: {project_item_id}")
        else:
            # Issue zaten projede olabilir, o zaman direkt sorguyla ID'yi alalım
            find_item_query = """
            query($project:ID!, $issue:ID!) {
              node(id: $project) {
                ... on ProjectV2 {
                  items(first: 100) {
                    nodes {
                      id
                      content {
                        ... on Issue {
                          id
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            
            find_resp = gql(find_item_query, {"project": project_id, "issue": issue_id})
            if find_resp:
                items = find_resp.get("data", {}).get("node", {}).get("items", {}).get("nodes", [])
                for item in items:
                    if item.get("content", {}).get("id") == issue_id:
                        project_item_id = item.get("id")
                        print(f"DEBUG: Found existing ProjectV2Item ID: {project_item_id}")
                        break
            
        if not project_item_id:
            print("❌ Issue'nun ProjectV2Item ID'si alınamadı.")
            return False
            
        # 3. Adım: Kartı Dev statüsüne taşı
        update_mutation = """
        mutation($project:ID!, $item:ID!, $field:ID!, $value:String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $project,
            itemId: $item,
            fieldId: $field,
            value: {
              singleSelectOptionId: $value
            }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """
        
        update_resp = gql(update_mutation, {
            "project": project_id,
            "item": project_item_id,
            "field": status_field_id,
            "value": dev_option_id
        })
        
        if update_resp and update_resp.get("data", {}).get("updateProjectV2ItemFieldValue"):
            print(f"✅ Issue #{issue_number} kartı başarıyla 'Dev' durumuna taşındı!")
            return True
        else:
            print(f"❌ Kart taşıma işlemi başarısız oldu. Response: {update_resp}")
            return False
            
    except Exception as e:
        print(f"❌ Kart işlemi sırasında hata: {str(e)}")
        return False

# ---------- Ana iş akışı ----------
def main():
    """Ana otomasyon adımlarını çalıştırır."""
    
    # 1) Proje, alan ve seçenek bilgilerini al
    try:
        project_id, status_field_id, dev_option_id = fetch_project_and_status_info()
    except ValueError as e:
        print(f"❌ Kritik Hata: Proje bilgileri alınamadı: {e}")
        return
    except Exception as e:
        print(f"❌ Beklenmedik Hata: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2) Branch oluştur veya var olanı kullan
    try:
        print(f"ℹ️ Checking/Creating branch: {BRANCH}")
        main_branch = repo.get_branch("main")
        main_sha = main_branch.commit.sha
        repo.create_git_ref(ref=f"refs/heads/{BRANCH}", sha=main_sha)
        print("🌿  Created branch", BRANCH)
    except GithubException as e:
        if e.status == 422 and isinstance(e.data, dict) and "Reference already exists" in e.data.get("message", ""):
            print("ℹ️  Branch exists; continue")
        else:
            print(f"❌ Error creating branch: {e.status} - {e.data}")
            return
    except Exception as e:
        print(f"❌ Unexpected error creating branch: {type(e).__name__} - {e}")
        return

    # 3) Boş dosyaları ekle (varsa atla)
    files_to_add = ("src/ecs/World.hpp", "src/ecs/World.cpp")
    print(f"ℹ️ Checking/Adding files: {files_to_add}")
    files_added_this_run = False
    for path in files_to_add:
        try:
            repo.get_contents(path, ref=BRANCH)
        except GithubException as e:
             if e.status == 404: # Dosya yoksa oluştur
                try:
                    commit_message = f"feat: add empty {os.path.basename(path)}"
                    repo.create_file(path, commit_message, "", branch=BRANCH)
                    print(f"➕  Added file: {path}")
                    files_added_this_run = True
                except GithubException as e_create:
                     print(f"❌ Error adding file {path}: {e_create.status} - {e_create.data}")
                except Exception as e_create_unexp:
                     print(f"❌ Unexpected error adding file {path}: {type(e_create_unexp).__name__} - {e_create_unexp}")
             else:
                 print(f"❌ Error checking file {path}: {e.status} - {e.data}")
        except Exception as e_check_unexp:
            print(f"❌ Unexpected error checking file {path}: {type(e_check_unexp).__name__} - {e_check_unexp}")

    # 4) PR aç / varsa yeniden kullan
    pr = None
    try:
        print(f"ℹ️ Checking/Creating Pull Request from branch {BRANCH} to main")
        pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{BRANCH}", base="main")
        if pulls.totalCount > 0:
            pr = pulls[0]
            print(f"🔗  PR #{pr.number} already exists: {pr.html_url}")
        else:
            pr_title = "feat: MVP‑1 World skeleton"
            pr_body = f"Closes #{ISSUE_NUMBER} – adds empty World class files."
            pr = repo.create_pull(title=pr_title, body=pr_body, base="main", head=BRANCH)
            print(f"🔗  PR #{pr.number} opened: {pr.html_url}")
    except GithubException as e_pr:
        print(f"❌ Error getting or creating PR: {e_pr.status} - {e_pr.data}")
    except Exception as e_pr_unexp:
        print(f"❌ Unexpected error with PR: {type(e_pr_unexp).__name__} - {e_pr_unexp}")

    if not pr:
        print("⚠️ Skipping issue update and Slack notification because PR is not available.")
        return

    # 5) Issue'u Dev'e taşı ve yorum ekle
    try:
        print(f"ℹ️ Updating issue #{ISSUE_NUMBER}")
        
        # Issue'yu projeye ekle/kartını taşı
        move_issue_card_to_dev(ISSUE_NUMBER, project_id, status_field_id, dev_option_id)
        
        # Issue'ya yorum ekle
        issue = repo.get_issue(ISSUE_NUMBER)
        comment_body = f"PR #{pr.number} linked."
        issue.create_comment(comment_body)
        print(f"💬 Comment added to issue #{ISSUE_NUMBER}: '{comment_body}'")

    except GithubException as e_issue:
         print(f"❌ Error interacting with issue #{ISSUE_NUMBER}: {e_issue.status} - {e_issue.data}")
    except Exception as e_issue_unexp:
        print(f"❌ Unexpected error interacting with issue #{ISSUE_NUMBER}: {type(e_issue_unexp).__name__} - {e_issue_unexp}")

    # 6) Slack ping
    try:
        print("ℹ️ Sending Slack notification...")
        slack_payload = {"text": SLACK_TEXT.format(pr=pr.number, url=pr.html_url)}
        slack_response = requests.post(SLACK, json=slack_payload, timeout=10)
        slack_response.raise_for_status()
        print("📢  Sent Slack notification")
    except requests.exceptions.RequestException as e_slack:
        print(f"⚠️ Error sending Slack notification: {e_slack}")
    except Exception as e_slack_unexp:
         print(f"⚠️ Unexpected error sending Slack notification: {type(e_slack_unexp).__name__} - {e_slack_unexp}")


if __name__ == "__main__":
    print("🚀 Orchestrator starting...")
    try:
        main()
    except Exception as e_main:
        print(f"🔥 Unhandled error in main execution: {type(e_main).__name__} - {e_main}")
        import traceback
        traceback.print_exc()
    finally:
        print("🏁 Orchestrator finished.")