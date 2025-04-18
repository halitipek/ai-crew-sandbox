#!/usr/bin/env python3
"""
SimplyECS – AI Orchestrator bootstrap
•  PR açar (varsa kullanır) ▸ #MVP‑1
•  Issue kartını Todo ▸ Dev taşır (Projects V2)
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
# X-Github-Next-Global-ID başlığını şimdilik kaldıralım, işe yaramadı.
HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
    # "X-Github-Next-Global-ID": "1" # <<<--- KALDIRILDI
}

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
        # Veri kısmı yoksa veya boşsa da None döndürelim (sorgu başarılı ama sonuç yoksa)
        if "data" not in json_resp or not json_resp["data"]:
             print(f"ℹ️ GraphQL query successful but returned no data or null data: {json_resp}")
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
def fetch_project_ids():
    """Proje ID'sini, Status alanı ID'sini ve 'Dev' seçeneği Global Node ID'sini alır."""
    owner, name = REPO_FULL.split("/")

    # 1) Proje ID’si
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

    # 2) Status Alanının Global ID'sini al
    q_field = """
    query($p:ID!){
      node(id:$p){
        ... on ProjectV2 {
          field(name:"Status"){
            ... on ProjectV2SingleSelectField {
              id # <<<--- Alanın kendi Global ID'si
              name
              # options { id name } # Artık seçenek ID'lerini buradan almıyoruz
            }
          }
        }
      }
    }"""
    field_resp = gql(q_field, {"p": project_id})
    if not field_resp: raise ValueError("Status alanı sorgusu başarısız.")
    try:
        sf = field_resp.get("data", {}).get("node", {}).get("field")
        if not sf: raise KeyError("'Status' alanı ('field') yanıtta bulunamadı.")
        status_field_id = sf.get("id")
        if not status_field_id: raise ValueError("Status alanı için 'id' değeri bulunamadı.")
        print(f"DEBUG: Found Status Field Global ID: {status_field_id}")
    except KeyError as e:
        raise ValueError(f"Status field ID'si alınırken yapı hatası: {e}") from e

    # 3) "Dev" Seçeneğinin Global Node ID'sini al (Yeni sorgu ile)
    q_option_node_id = """
    query($field_id: ID!, $option_name: String!) {
      node(id: $field_id) {
        ... on ProjectV2SingleSelectField {
          options(filterBy: {name: $option_name}, first: 1) {
            nodes {
              id # <<<--- Bu ID'nin Global Node ID olmasını bekliyoruz
              name
            }
          }
        }
      }
    }
    """
    dev_option_name = "Dev"
    option_resp = gql(q_option_node_id, {"field_id": status_field_id, "option_name": dev_option_name})
    if not option_resp: raise ValueError(f"'{dev_option_name}' seçeneği için Node ID sorgusu başarısız.")
    try:
        # Yanıtı dikkatlice ayrıştır
        options_nodes = option_resp.get("data", {}).get("node", {}).get("options", {}).get("nodes", [])
        if not options_nodes:
            # Seçenek bulunamadıysa daha net hata ver
            raise ValueError(f"'{dev_option_name}' isimli seçenek Status alanı ({status_field_id}) içinde bulunamadı.")

        dev_option_node_id = options_nodes[0].get("id")
        if not dev_option_node_id:
             raise ValueError(f"'{dev_option_name}' seçeneği bulundu ancak Global Node ID ('id') alınamadı.")
        print(f"DEBUG: Found '{dev_option_name}' option Global Node ID: {dev_option_node_id}")

    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"'{dev_option_name}' seçeneğinin Node ID'si alınırken yapı hatası: {e}. Yanıt: {option_resp}") from e

    # Sonuçları döndür
    print("🗂️  Status field ID:", status_field_id[:8], "…  Dev option ID:", dev_option_node_id[:8], "…")
    return project_id, status_field_id, dev_option_node_id


# --- Fonksiyon çağrısı ve sonrası ---
try:
    PROJECT_ID, STATUS_FIELD_ID, DEV_OPTION_ID = fetch_project_ids()
except ValueError as e:
    print(f"❌ Kritik Hata: Proje/Alan/Seçenek ID'leri alınamadı. {e}")
    exit(1)
except Exception as e: # Beklenmedik diğer hatalar için
    print(f"❌ Beklenmedik Hata (fetch_project_ids): {type(e).__name__} - {e}")
    import traceback
    traceback.print_exc()
    exit(1)


# ---------- Kartı taşı ----------
# Bu fonksiyon aynı kalabilir, artık doğru DEV_OPTION_ID ile çağrılacak
def move_issue_to_dev(item_id: str):
    """Verilen issue'nun proje kartını 'Dev' statüsüne taşır."""
    mut = """
    mutation($proj:ID!,$item:ID!,$field:ID!,$opt:ID!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$proj itemId:$item fieldId:$field
        value:{ singleSelectOptionId:$opt }})
      {
        projectV2Item { id }
      }
    }"""
    print(f"DEBUG: Attempting to move item '{item_id}' using field '{STATUS_FIELD_ID}' and option '{DEV_OPTION_ID}'")
    move_resp = gql(mut, {"proj": PROJECT_ID, "item": item_id,
                          "field": STATUS_FIELD_ID, "opt": DEV_OPTION_ID})

    if move_resp and move_resp.get("data", {}).get("updateProjectV2ItemFieldValue", {}).get("projectV2Item"):
        moved_item_id = move_resp['data']['updateProjectV2ItemFieldValue']['projectV2Item'].get('id', 'Bilinmiyor')
        print(f"✅  Moved card to Dev (Item ID: {moved_item_id[:8]}...)")
    else:
        print(f"⚠️ Warning: Card move failed or API response was unexpected. Response from gql: {move_resp}")
        # raise RuntimeError("Kart taşıma işlemi başarısız oldu.") # İsteğe bağlı


# ---------- Ana iş akışı ----------
# main fonksiyonu ve sonrası aynı kalabilir...
def main():
    """Ana otomasyon adımlarını çalıştırır."""
    # 1) Branch oluştur veya var olanı kullan
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

    # 2) Boş dosyaları ekle (varsa atla)
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

    # 3) PR aç / varsa yeniden kullan
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

    # 4) Issue’u Dev’e taşı ve yorum ekle
    try:
        print(f"ℹ️ Updating issue #{ISSUE_NUMBER}")
        issue = repo.get_issue(ISSUE_NUMBER)
        item_id = getattr(issue, "node_id", None) or issue.raw_data.get("node_id")
        if not item_id:
             print(f"❌ Error: Could not get node_id (project item ID) for issue #{ISSUE_NUMBER}")
        else:
            try:
                move_issue_to_dev(item_id)
            except Exception as e_move:
                 print(f"❌ Error during card move: {type(e_move).__name__} - {e_move}")

        comment_body = f"PR #{pr.number} linked."
        issue.create_comment(comment_body)
        print(f"💬 Comment added to issue #{ISSUE_NUMBER}: '{comment_body}'")

    except GithubException as e_issue:
         print(f"❌ Error interacting with issue #{ISSUE_NUMBER}: {e_issue.status} - {e_issue.data}")
    except Exception as e_issue_unexp:
        print(f"❌ Unexpected error interacting with issue #{ISSUE_NUMBER}: {type(e_issue_unexp).__name__} - {e_issue_unexp}")

    # 5) Slack ping
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