#!/usr/bin/env python3
"""
SimplyECS – Core Engineers AI
• PR onaylandığında tetiklenir
• Issue'daki görevleri gerçekleştirir
• C++ kodunu yazar ve PR'a ekler
• Tamamlandığında QA/Perf'i tetikler
"""

import os
import sys
import json
import yaml
import requests
import time
from github import Github, GithubException
import openai

# ---------- Ayarlar ----------
REPO_FULL = "halitipek/ai-crew-sandbox"

# Config'den model bilgilerini oku
def load_config():
    try:
        with open('crew_config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            return config.get('crew', {})
    except Exception as e:
        print(f"❌ Config dosyası okunamadı: {str(e)}")
        return {}

CONFIG = load_config()
CORE_ENG_1_MODEL = CONFIG.get('core_eng_1', {}).get('model', 'gpt-3.5-turbo-0125')
CORE_ENG_2_MODEL = CONFIG.get('core_eng_2', {}).get('model', 'gpt-3.5-turbo-0125')

# Ortam değişkenlerini kontrol et
TOKEN = os.environ.get("GH_PAT")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK")
PR_NUMBER = os.environ.get("PR_NUMBER")

# Ortam değişkenlerini doğrula
if not TOKEN:
    print("❌ Hata: GH_PAT ortam değişkeni ayarlanmamış.")
    sys.exit(1)
if not OPENAI_API_KEY:
    print("❌ Hata: OPENAI_API_KEY ortam değişkeni ayarlanmamış.")
    sys.exit(1)
if not SLACK_WEBHOOK:
    print("❌ Hata: SLACK_WEBHOOK ortam değişkeni ayarlanmamış.")
    sys.exit(1)
if not PR_NUMBER:
    print("❌ Hata: PR_NUMBER ortam değişkeni ayarlanmamış.")
    sys.exit(1)

# API'leri yapılandır
gh = Github(TOKEN)
repo = gh.get_repo(REPO_FULL)
openai.api_key = OPENAI_API_KEY

# ---------- Yardımcı Fonksiyonlar ----------
def notify_slack(message):
    """Slack'e bildirim gönderir."""
    try:
        payload = {"text": message}
        response = requests.post(SLACK_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Slack bildirimi gönderilemedi: {e}")
        return False

def get_pr(pr_number):
    """PR nesnesini getirir."""
    try:
        return repo.get_pull(int(pr_number))
    except GithubException as e:
        print(f"❌ PR alınırken hata oluştu: {e.status} - {e.data}")
        return None

def get_issue_from_pr(pr):
    """PR'a bağlı issue'yu bulur."""
    try:
        # PR açıklamasından issue referansını bul (örn: "Closes #1")
        body = pr.body or ""
        issue_refs = [word for word in body.split() if word.startswith('#')]
        
        if not issue_refs:
            print("⚠️ PR açıklamasında issue referansı bulunamadı.")
            return None
        
        # İlk issue referansını kullan
        issue_number = int(issue_refs[0].strip('#'))
        return repo.get_issue(issue_number)
    except Exception as e:
        print(f"❌ Issue bilgisi alınırken hata oluştu: {str(e)}")
        return None

def get_file_content(pr, file_path):
    """PR'da belirtilen dosya yolundaki içeriği getirir."""
    try:
        content = repo.get_contents(file_path, ref=pr.head.ref)
        return content.decoded_content.decode('utf-8')
    except Exception as e:
        print(f"⚠️ Dosya içeriği alınamadı {file_path}: {e}")
        return None

def update_file(pr, file_path, content, commit_message):
    """Belirtilen dosyayı günceller veya oluşturur."""
    try:
        # Önce dosyanın mevcut içeriğini ve SHA'sını almaya çalış
        try:
            file_content = repo.get_contents(file_path, ref=pr.head.ref)
            sha = file_content.sha
            # Dosya var, güncelle
            repo.update_file(file_path, commit_message, content, sha, branch=pr.head.ref)
            print(f"✅ Dosya güncellendi: {file_path}")
        except:
            # Dosya yok, oluştur
            repo.create_file(file_path, commit_message, content, branch=pr.head.ref)
            print(f"✅ Dosya oluşturuldu: {file_path}")
        
        return True
    except Exception as e:
        print(f"❌ Dosya güncellenirken/oluşturulurken hata: {str(e)}")
        return False

def generate_code(prompt, model=CORE_ENG_1_MODEL):
    """AI modeli kullanarak kod üretir."""
    try:
        system_message = """
        Sen bir C++ kütüphanesi geliştiren takımın deneyimli bir yazılım mühendisisin. 
        SimplyECS (Entity Component System) kütüphanesi için kod yazıyorsun.
        
        Aşağıdaki kriterlere göre kod yazmalısın:
        
        1. Modern C++ (C++17/20) kullan
        2. Performansı optimize et - ECS sistemleri maksimum verimlilik gerektirir
        3. Veri odaklı tasarım prensiplerine uy (cache dostu, bellek verimli)
        4. Okunabilir, bakımı kolay ve iyi dökümante edilmiş kod yaz
        5. Güvenli bellek yönetimi ve doğru hata kontrolü yap
        
        İstenen görev ve detayları dikkatlice oku, belirtilen dosya yollarına uygun şekilde kod üret.
        """
        
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=4000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ AI kod üretimi sırasında hata oluştu: {str(e)}")
        return None

def analyze_issue(issue_content):
    """Issue içeriğini analiz ederek görevleri çıkarır."""
    try:
        prompt = f"""
        Aşağıdaki GitHub issue içeriğini analiz et ve yapılması gereken işleri belirle.
        Görevleri, dosya yollarını ve gerekli kodlama görevlerini liste halinde çıkar.
        
        Issue içeriği:
        {issue_content}
        
        Analiz sonucunda şunları belirle:
        1. Hangi dosyalar oluşturulmalı veya değiştirilmeli?
        2. Her dosyada ne tür işlevsellik eklenmeli?
        3. Eklenecek kodun amacı ve teknik detayları neler?
        """
        
        response = openai.chat.completions.create(
            model=CORE_ENG_1_MODEL,
            messages=[
                {"role": "system", "content": "Sen bir görev analizi yapan yazılım mühendisisin."},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=2000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ Issue analizi sırasında hata oluştu: {str(e)}")
        return None

def implement_task(task_description, file_path):
    """Belirtilen görevi ve dosya yolunu kullanarak kod üretir."""
    try:
        # Dosya uzantısından dil türünü belirle
        ext = file_path.split('.')[-1].lower()
        language = "C++" if ext in ["cpp", "hpp", "h", "cc", "cxx"] else "Unknown"
        
        prompt = f"""
        Aşağıdaki görev için {language} kodu yazın:
        
        Dosya: {file_path}
        
        Görev açıklaması:
        {task_description}
        
        Lütfen dosya için tam ve eksiksiz kod üretin. İskelet veya kısmi çözüm değil,
        tamamen çalışan bir implementasyon bekliyoruz.
        """
        
        # Farklı model seçimleri arasında denge kuralım
        model = CORE_ENG_1_MODEL if hash(file_path) % 2 == 0 else CORE_ENG_2_MODEL
        
        return generate_code(prompt, model)
    
    except Exception as e:
        print(f"❌ Görev implementasyonu sırasında hata oluştu: {str(e)}")
        return None

def process_pr():
    """PR'ı işler ve gerekli kod değişikliklerini yapar."""
    try:
        pr = get_pr(PR_NUMBER)
        if not pr:
            print("❌ PR bulunamadı.")
            return False
        
        # PR'ın durumunu kontrol et
        if pr.state != "open":
            print(f"⚠️ PR #{PR_NUMBER} açık değil, durumu: {pr.state}")
            return False
        
        print(f"ℹ️ PR #{PR_NUMBER} inceleniyor: {pr.title}")
        
        # PR'a bağlı issue'yu bul
        issue = get_issue_from_pr(pr)
        if not issue:
            print("⚠️ PR'a bağlı issue bulunamadı.")
            return False
        
        print(f"ℹ️ Issue #{issue.number} bulundu: {issue.title}")
        
        # Issue içeriğini analiz et ve görevleri belirle
        issue_analysis = analyze_issue(issue.title + "\n\n" + (issue.body or ""))
        if not issue_analysis:
            print("❌ Issue analizi başarısız oldu.")
            return False
        
        print(f"📋 Issue analizi tamamlandı. Görevler belirlendi.")
        print(issue_analysis)
        
        # PR'daki dosyaları incele
        pr_files = list(pr.get_files())
        tasks = []
        
        for file in pr_files:
            file_path = file.filename
            print(f"ℹ️ Dosya inceleniyor: {file_path}")
            
            # Dosya içeriği boş mu kontrol et (Orchestrator boş dosya oluşturmuş olabilir)
            file_content = get_file_content(pr, file_path)
            
            if not file_content or file_content.strip() == "":
                print(f"ℹ️ Dosya boş, doldurulacak: {file_path}")
                tasks.append({
                    "file_path": file_path,
                    "is_empty": True
                })
            else:
                print(f"ℹ️ Dosya zaten içerik içeriyor: {file_path}")
        
        # Görevleri uygula ve dosyaları güncelle
        for task in tasks:
            file_path = task["file_path"]
            
            # Issue analizini kullanarak dosya için kod üret
            task_description = f"""
            Issue analizi:
            {issue_analysis}
            
            Lütfen bu dosyayı implement edin: {file_path}
            """
            
            code = implement_task(task_description, file_path)
            if not code:
                print(f"❌ Kod üretimi başarısız oldu: {file_path}")
                continue
            
            # Dosyayı güncelle
            commit_message = f"feat: implement {os.path.basename(file_path)}"
            update_result = update_file(pr, file_path, code, commit_message)
            
            if update_result:
                print(f"✅ {file_path} başarıyla güncellendi.")
            else:
                print(f"❌ {file_path} güncellenirken hata oluştu.")
        
        # İşlem tamamlandı, PR'a yorum ekle
        comment = f"""
        ## 🛠️ Core Engineers Raporu
        
        Issue #{issue.number} için kod geliştirildi.
        
        **Güncellenen dosyalar:**
        {chr(10).join(['- ' + task['file_path'] for task in tasks])}
        
        **İşlem özeti:**
        {issue_analysis}
        
        Kodlar hazır, inceleme için QA/Perf ekibine aktarılıyor.
        """
        
        pr.create_issue_comment(comment)
        
        # Slack'e bildirim gönder
        notify_slack(f":gear: Core Engineers, PR #{PR_NUMBER} için kod geliştirmesini tamamladı!")
        
        return True
        
    except Exception as e:
        print(f"❌ PR işlenirken beklenmeyen hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ---------- Ana İş Akışı ----------
def main():
    """Core Engineers'ın ana iş akışı."""
    print("🧑‍💻 Core Engineers başlatılıyor...")
    
    success = process_pr()
    
    if success:
        print(f"✅ PR #{PR_NUMBER} başarıyla işlendi ve kodlar eklendi.")
        
        # QA/Perf ekibini tetikle
        print("ℹ️ QA/Perf ekibini tetikleme işlemi burada yapılacak...")
        # TODO: QA/Perf ekibini tetikleyen kod eklenecek
    else:
        print(f"❌ PR #{PR_NUMBER} işlenirken hatalar oluştu.")
        
        # Hata durumunda Slack'e bildirim
        notify_slack(f":warning: Core Engineers, PR #{PR_NUMBER} işlenirken sorun yaşadı!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"🔥 Core Engineers'ta kritik hata: {str(e)}")
        import traceback
        traceback.print_exc()
        notify_slack(f":boom: Core Engineers'ta kritik hata: {str(e)}")
    finally:
        print("🏁 Core Engineers tamamlandı.")