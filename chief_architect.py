#!/usr/bin/env python3
"""
SimplyECS – Chief Architect AI
• PR'ları inceler
• Kodlama standartlarını kontrol eder
• Geliştirme önerilerinde bulunur
• Onay veya revizyon ister
"""

import os
import sys
import json
import yaml
import requests
from github import Github, GithubException
from openai import OpenAI

# ---------- Ayarlar ----------
REPO_FULL = "halitipek/ai-crew-sandbox"

# Config'den model bilgilerini oku
def load_config():
    try:
        with open('crew_config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            return config.get('crew', {})
    except Exception as e:
        print(f"ℹ️ Config dosyası okunamadı, varsayılan model kullanılacak: {str(e)}")
        return {}

CONFIG = load_config()
MODEL_ID = CONFIG.get('chief_architect', {}).get('model', 'gpt-3.5-turbo-0125')

# Ortam değişkenlerini kontrol et
TOKEN = os.environ.get("GH_PAT")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
PR_NUMBER = os.environ.get("PR_NUMBER")

# API'leri yapılandır
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

# Github bağlantısı için token kontrolü
if not TOKEN:
    print("❌ Hata: GH_PAT ortam değişkeni ayarlanmamış.")
    sys.exit(1)

gh = Github(TOKEN)
repo = gh.get_repo(REPO_FULL)

# ---------- Yardımcı Fonksiyonlar ----------
def notify_slack(message):
    """Slack'e bildirim gönderir."""
    if not SLACK_WEBHOOK:
        print("ℹ️ SLACK_WEBHOOK ortam değişkeni ayarlanmamış, bildirim gönderilemiyor.")
        return False
        
    try:
        payload = {"text": message}
        response = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Slack bildirimi gönderilemedi: {e}")
        return False

def get_pr(pr_number=None):
    """Belirli bir PR'ı veya tüm bekleyen PR'ları alır."""
    try:
        if pr_number:
            # Belirli PR numarası verilmişse onu getir
            return repo.get_pull(int(pr_number))
        else:
            # Bekleyen tüm PR'ları getir
            open_prs = repo.get_pulls(state="open")
            pending_review = []
            
            for pr in open_prs:
                # PR'ın review durumunu kontrol et
                reviews = pr.get_reviews()
                has_approval = any(review.state == "APPROVED" for review in reviews)
                has_changes_requested = any(review.state == "CHANGES_REQUESTED" for review in reviews)
                
                # Henüz incelenmemiş veya changes requested olan PR'ları dahil et
                if not has_approval and not has_changes_requested:
                    pending_review.append(pr)
                    
            return pending_review
    except GithubException as e:
        print(f"❌ PR'lar alınırken hata oluştu: {e.status} - {e.data}")
        return [] if pr_number is None else None

def get_file_changes(pr):
    """PR'daki değişiklikleri alır."""
    try:
        files = pr.get_files()
        changes = []
        
        for file in files:
            # Dosya içeriğini al (eğer silinmemişse)
            content = None
            if file.status != "removed":
                try:
                    content_file = repo.get_contents(file.filename, ref=pr.head.ref)
                    content = content_file.decoded_content.decode('utf-8')
                except Exception as e:
                    print(f"⚠️ Dosya içeriği alınamadı {file.filename}: {e}")
            
            changes.append({
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "content": content
            })
            
        return changes
    except GithubException as e:
        print(f"❌ Dosya değişiklikleri alınırken hata oluştu: {e.status} - {e.data}")
        return []

def review_code(pr_title, pr_body, changes):
    """AI modeli kullanarak kod incelemesi yapar."""
    if not client:
        print("❌ OpenAI API anahtarı ayarlanmamış, kod incelemesi yapılamıyor.")
        return "OpenAI API anahtarı eksik olduğu için kod incelemesi yapılamadı. Lütfen OPENAI_API_KEY ortam değişkenini ayarlayın."
    
    try:
        code_blocks = []
        for change in changes:
            if change["content"]:
                code_blocks.append(f"Dosya: {change['filename']} ({change['status']})\n"
                                  f"Eklemeler: {change['additions']}, Silmeler: {change['deletions']}\n"
                                  f"```\n{change['content']}\n```")
            else:
                code_blocks.append(f"Dosya: {change['filename']} ({change['status']})\n"
                                  f"Eklemeler: {change['additions']}, Silmeler: {change['deletions']}\n"
                                  f"İçerik kullanılamıyor.")
        
        code_content = "\n\n".join(code_blocks)
        
        system_message = """
        Sen bir C++ kütüphanesi geliştiren takımın baş mimarısın. SimplyECS (Entity Component System) kütüphanesi 
        için kod incelemesi yapıyorsun. Aşağıdaki kriterlere göre kodu değerlendir:
        
        1. Kodlama standartları: Modern C++ (C++17/20) kullanımı, doğru bellek yönetimi
        2. Performans: ECS sistemlerinde performans kritiktir, gereksiz kopyalar ve verimsiz algoritmaları kontrol et
        3. Tasarım: ECS tasarım prensiplerine (veri odaklı tasarım, cache uyumluluğu) uygunluk
        4. Okunabilirlik: Açık ve anlaşılır kod, uygun dökümantasyon
        5. Test edilebilirlik: Birim testler için uygun tasarım
        
        İnceleme sonucunda şunları belirt:
        1. Genel değerlendirme (olumlu ve olumsuz yönler)
        2. Belirli geliştirme önerileri (kod örnekleriyle)
        3. PR'ın mevcut haliyle kabul edilip edilmeyeceği (APPROVED veya CHANGES_REQUESTED)
        
        Teknik detaylara gir, ancak yapıcı ve yardımcı ol.
        """
        
        user_message = f"""
        PR Başlığı: {pr_title}
        PR Açıklaması: {pr_body}
        
        Kod değişiklikleri:
        
        {code_content}
        """
        
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=1,
            max_completion_tokens=2000  # max_tokens yerine max_completion_tokens kullan
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ AI incelemesi sırasında hata oluştu: {str(e)}")
        return "AI incelemesi sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin."

def add_review_comment(pr, review_text):
    """PR'a yorum olarak inceleme ekler."""
    try:
        # PR'a yorum olarak ekle (GitHub review yerine)
        pr.create_issue_comment(f"## 🧠 Chief Architect İncelemesi\n\n{review_text}")
        print(f"✅ PR #{pr.number} için inceleme yorumu eklendi.")
        
        # PR otomatik olarak onaylanır (Core Engineers'ı tetiklemek için)
        pr.create_review(body="Bu PR otomatik olarak onaylanmıştır.", event="APPROVE")
        print(f"✅ PR #{pr.number} otomatik olarak onaylandı.")
        
        return True
    except GithubException as e:
        # Kendi PR'ınızı onaylayamazsınız hatası (422)
        if e.status == 422:
            print(f"ℹ️ PR #{pr.number} onaylanamadı (kendi PR'ınızı onaylayamazsınız). Sadece yorum ekleniyor.")
            return True
        print(f"❌ PR #{pr.number} için inceleme yorumu eklenirken hata: {e.status} - {e.data}")
        return False

# ---------- Ana İş Akışı ----------
def main():
    """Chief Architect'in ana iş akışı."""
    print("🧠 Chief Architect başlatılıyor...")
    
    # PR numarası belirlendi mi kontrol et
    if PR_NUMBER:
        # Belirli PR'ı incele
        pr = get_pr(PR_NUMBER)
        if not pr:
            print(f"❌ PR #{PR_NUMBER} bulunamadı.")
            return
        
        prs_to_review = [pr]
        print(f"ℹ️ PR #{PR_NUMBER} incelenecek.")
    else:
        # Tüm bekleyen PR'ları incele
        prs_to_review = get_pr()
        if not prs_to_review:
            print("ℹ️ İnceleme bekleyen PR bulunmuyor.")
            return
        
        print(f"🔍 {len(prs_to_review)} adet inceleme bekleyen PR bulundu.")
    
    for pr in prs_to_review:
        try:
            print(f"📋 PR #{pr.number} inceleniyor: {pr.title}")
            
            # PR değişikliklerini al
            changes = get_file_changes(pr)
            
            # Değişiklik yoksa atla
            if not changes:
                print(f"ℹ️ PR #{pr.number}'de incelenecek değişiklik bulunmuyor.")
                continue
            
            # AI ile kod incelemesi yap
            review_result = review_code(pr.title, pr.body, changes)
            
            # İnceleme sonucunu PR'a yorum olarak ekle
            add_review_comment(pr, review_result)
            
            # Slack bildirimi gönder
            notify_slack(f":brain: Chief Architect PR #{pr.number} incelemesini tamamladı!")
            
            print(f"✅ PR #{pr.number} incelemesi tamamlandı")
            
        except Exception as e:
            print(f"❌ PR #{pr.number} incelenirken hata oluştu: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"🔥 Chief Architect'te kritik hata: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("🏁 Chief Architect tamamlandı.")