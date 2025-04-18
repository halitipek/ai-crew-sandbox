#!/usr/bin/env python3
"""
SimplyECS – AI Orchestrator bootstrap
•  PR açar (varsa kullanır) ▸ #MVP‑1
•  Issue kartını Todo ▸ Dev taşır (Projects V2)
•  Slack ping gönderir
"""

import os, requests, textwrap, json # json import edildi
from github import Github, GithubException

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
    # Yanıtı kontrol et (hata varsa exception fırlatır)
    try:
        resp.raise_for_status()
        json_resp = resp.json()
        # GraphQL seviyesinde hata var mı kontrol et
        if "errors" in json_resp:
            print(f"❌ GraphQL Query Error: {json.dumps(json_resp['errors'], indent=2)}")
            # Hatanın ciddiyetine göre burada çıkış yapabilir veya None döndürebilirsiniz
            # Bu örnekte None döndürelim, çağıran taraf kontrol etsin
            return None
        return json_resp
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Request Error: {e}")
        return None # veya raise e
    except json.JSONDecodeError as e:
        print(f"❌ JSON Decode Error: {e} - Response text: {resp.text[:500]}") # Yanıtın başını göster
        return None # veya raise e


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
    proj_resp = gql(q_proj, {"o": owner, "n": name})
    # gql'den None dönme ihtimalini kontrol et
    if not proj_resp or "data" not in proj_resp:
         raise ValueError("Proje ID'si sorgusu başarısız oldu veya veri dönmedi.")

    data = proj_resp["data"]
    nodes = data.get("viewer", {}).get("projectsV2", {}).get("nodes", []) + \
            data.get("repository", {}).get("projectsV2", {}).get("nodes", [])
    if not nodes:
        raise ValueError("Proje bulunamadı (ne kullanıcıda ne de repoda).")

    # Projeyi daha güvenli bulma
    proj = next((n for n in nodes if n and "SimplyECS" in n.get("title", "")), None)
    if not proj:
        # SimplyECS bulunamazsa ilk projeyi kullanmak yerine hata verelim
        # proj = nodes[0] # Eski davranış
        raise ValueError("Projeler arasında 'SimplyECS' içeren bir proje bulunamadı.")

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
              options { id name } # Seçenek ID'lerini alıyoruz
            }
          }
        }
      }
    }"""
    field_resp = gql(q_field, {"p": project_id})
    # gql'den None dönme ihtimalini kontrol et
    if not field_resp or "data" not in field_resp:
        raise ValueError("Status alanı sorgusu başarısız oldu veya veri dönmedi.")

    try:
        # Daha güvenli erişim için .get() kullan
        node_data = field_resp.get("data", {}).get("node")
        if not node_data:
             raise KeyError("'node' anahtarı yanıtta bulunamadı.")
        sf = node_data.get("field") # Status field verisi
        if not sf:
             raise KeyError("'field' (Status alanı) yanıtta bulunamadı veya null.")

        print(f"DEBUG: Status Field Data (sf): {json.dumps(sf, indent=2)}") # Gelen tüm Status field verisini gör
        field_id = sf.get("id") # Status alanının ID'si
        if not field_id:
            raise ValueError("Status alanı için 'id' bulunamadı.")

        options = sf.get("options", [])
        if not options:
             raise ValueError("Status alanı için 'options' bulunamadı veya boş.")

        # "Dev" seçeneğini bul ve onun ID'sini al (Bu proje içi ID)
        dev_option = next((o for o in options if o and o.get("name", "").lower() == "dev"), None)
        if not dev_option:
            # StopIteration yerine daha açıklayıcı hata
            raise ValueError("'Status' alanında 'Dev' isimli seçenek bulunamadı!")

        dev_opt = dev_option.get("id")
        if not dev_opt:
             raise ValueError("'Dev' seçeneği bulundu ancak 'id' değeri yok.")

        print(f"DEBUG: Found 'Dev' option ID: {dev_opt}")

    except KeyError as e:
        print(f"HATA: API yanıtında beklenen yapı bulunamadı. Anahtar hatası: {e}. Yanıt: {field_resp}")
        raise ValueError(f"Status field verisi alınırken yapı hatası: {e}") from e
    # StopIteration artık oluşmamalı, ValueError ile yakalıyoruz.

    # ----- ID ÇEVİRME ADIMI TAMAMEN KALDIRILDI -----

    print("🗂️  Status field ID:", field_id[:8], "…  Dev option ID:", dev_opt) # Seçenek ID'sinin tamamını göster
    return project_id, field_id, dev_opt # İlk bulunan dev_opt ID'sini döndür


# --- Fonksiyon çağrısı ve sonrası (Hata yakalama ile) ---
try:
    PROJECT_ID, STATUS_FIELD_ID, DEV_OPTION_ID = fetch_project_ids()
except ValueError as e:
    print(f"❌ Kritik Hata: Proje/Alan ID'leri alınamadı. {e}")
    exit(1) # ID'ler olmadan devam edilemez, çıkış yap
except Exception as e: # Beklenmedik diğer hatalar için
    print(f"❌ Beklenmedik Hata (fetch_project_ids): {type(e).__name__} - {e}")
    exit(1)


# ---------- Kartı taşı ----------
def move_issue_to_dev(item_id: str):
    mut = """
    mutation($proj:ID!,$item:ID!,$field:ID!,$opt:ID!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$proj itemId:$item fieldId:$field
        value:{ singleSelectOptionId:$opt }}) # Burası seçenek ID'sini bekler
      { item { id } }}
    """
    move_resp = gql(mut, {"proj": PROJECT_ID, "item": item_id,
                          "field": STATUS_FIELD_ID, "opt": DEV_OPTION_ID})
    # Taşıma işleminin sonucunu kontrol et (opsiyonel ama önerilir)
    if move_resp and move_resp.get("data", {}).get("updateProjectV2ItemFieldValue"):
        print("✅  Moved card to Dev")
    else:
        print(f"⚠️ Warning: Card move API call completed but response structure might be unexpected or indicate failure. Response: {move_resp}")


# ---------- Ana iş akışı ----------
def main():
    # 1) Branch oluştur
    try:
        main_branch = repo.get_branch("main")
        main_sha = main_branch.commit.sha
        repo.create_git_ref(ref=f"refs/heads/{BRANCH}", sha=main_sha)
        print("🌿  Created branch", BRANCH)
    except GithubException as e: # Daha spesifik Github hatası yakala
        if e.status == 422 and "Reference already exists" in str(e.data.get("message", "")):
            print("ℹ️  Branch exists; continue")
        else:
            print(f"❌ Error creating branch: {e.status} - {e.data}")
            return # Branch oluşturulamazsa devam etme
    except Exception as e:
        print(f"❌ Unexpected error creating branch: {e}")
        return

    # 2) Boş dosyaları ekle
    files_added = False
    for path in ("src/ecs/World.hpp","src/ecs/World.cpp"):
        try:
            repo.get_contents(path, ref=BRANCH)
            # print(f"ℹ️ File exists: {path}") # İsteğe bağlı bilgi mesajı
        except GithubException as e:
             if e.status == 404: # Dosya yoksa oluştur
                try:
                    repo.create_file(path, f"feat: add {path}", "", branch=BRANCH)
                    print("➕  Added", path)
                    files_added = True
                except GithubException as e_create:
                     print(f"❌ Error adding file {path}: {e_create.status} - {e_create.data}")
                except Exception as e_create_unexp:
                     print(f"❌ Unexpected error adding file {path}: {e_create_unexp}")
             else:
                 print(f"❌ Error checking file {path}: {e.status} - {e.data}")
        except Exception as e_check_unexp:
            print(f"❌ Unexpected error checking file {path}: {e_check_unexp}")


    # 3) PR aç / varsa yeniden kullan
    pr = None # PR objesini başlangıçta None yapalım
    try:
        pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{BRANCH}")
        if pulls.totalCount > 0:
            pr = pulls[0]
            print("🔗  PR already exists:", pr.html_url)
        else:
             # Sadece dosya eklendiyse veya hiç dosya yoksa PR açmayı dene
             # (Bu mantık projenize göre değişebilir)
            pr = repo.create_pull(
                title="feat: MVP‑1 World skeleton",
                body=f"Closes #{ISSUE_NUMBER} – adds empty World class files.",
                base="main", head=BRANCH
            )
            print("🔗  PR opened:", pr.html_url)
    except GithubException as e_pr:
        print(f"❌ Error getting or creating PR: {e_pr.status} - {e_pr.data}")
        # PR yoksa sonraki adımlar (kart taşıma, yorum ekleme) mantıksız olabilir
        # return # İsteğe bağlı olarak burada çıkılabilir
    except Exception as e_pr_unexp:
        print(f"❌ Unexpected error with PR: {e_pr_unexp}")
        # return

    # PR objesi alındıysa veya oluşturulduysa devam et
    if not pr:
        print("⚠️ Skipping issue update and Slack notification because PR is not available.")
        return

    # 4) Issue’u Dev’e taşı ve yorum ekle
    try:
        issue = repo.get_issue(ISSUE_NUMBER)
        # issue objesinde node_id attribute'u yoksa raw_data'dan almayı dene
        item_id = getattr(issue, "node_id", issue.raw_data.get("node_id"))
        if not item_id:
             print(f"❌ Error: Could not get node_id for issue #{ISSUE_NUMBER}")
             # item_id olmadan taşıma yapılamaz, ama yorum eklenebilir belki?
        else:
            move_issue_to_dev(item_id) # Kart taşıma fonksiyonunu çağır

        # Yorum ekle
        issue.create_comment(f"PR #{pr.number} linked")
        print(f"💬 Comment added to issue #{ISSUE_NUMBER}")

    except GithubException as e_issue:
         print(f"❌ Error interacting with issue #{ISSUE_NUMBER}: {e_issue.status} - {e_issue.data}")
    except Exception as e_issue_unexp:
        print(f"❌ Unexpected error interacting with issue #{ISSUE_NUMBER}: {e_issue_unexp}")


    # 5) Slack ping
    try:
        slack_response = requests.post(SLACK, json={"text": SLACK_TEXT.format(pr=pr.number, url=pr.html_url)}, timeout=10)
        slack_response.raise_for_status() # HTTP hatası varsa exception fırlat
        print("📢  Sent Slack notification")
    except requests.exceptions.RequestException as e_slack:
        print(f"⚠️ Error sending Slack notification: {e_slack}")
    except Exception as e_slack_unexp:
         print(f"⚠️ Unexpected error sending Slack notification: {e_slack_unexp}")


if __name__ == "__main__":
    print("🚀 Orchestrator starting...")
    main()
    print("🏁 Orchestrator finished.")