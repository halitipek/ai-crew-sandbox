#!/usr/bin/env python3
"""
SimplyECS – QA/Perf AI
• Core Engineers kodları tamamladığında tetiklenir
• Test ve benchmark kodları üretir
• Performans hedeflerini doğrular
• CI sonuçlarını analiz eder
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
QA_PERF_MODEL = CONFIG.get('qa_perf', {}).get('model', 'gpt-3.5-turbo-0125')

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

def get_pr_files(pr):
    """PR'daki dosyaları alır ve dosya türlerine göre gruplanır."""
    try:
        files = list(pr.get_files())
        
        # Dosyaları türlerine göre grupla
        grouped_files = {
            "cpp": [],      # C++ impl dosyaları
            "hpp": [],      # C++ header dosyaları
            "inl": [],      # C++ inline impl dosyaları
            "tests": [],    # Test dosyaları
            "benchmark": [], # Benchmark dosyaları
            "cmake": [],    # CMake dosyaları
            "other": []     # Diğer dosyalar
        }
        
        for file in files:
            path = file.filename
            ext = path.split('.')[-1].lower()
            
            if "test" in path.lower() or path.startswith("tests/"):
                grouped_files["tests"].append(path)
            elif "benchmark" in path.lower():
                grouped_files["benchmark"].append(path)
            elif ext == "cpp" or ext == "cc" or ext == "cxx":
                grouped_files["cpp"].append(path)
            elif ext == "hpp" or ext == "h" or ext == "hxx":
                grouped_files["hpp"].append(path)
            elif ext == "inl":
                grouped_files["inl"].append(path)
            elif path == "CMakeLists.txt" or path.endswith(".cmake"):
                grouped_files["cmake"].append(path)
            else:
                grouped_files["other"].append(path)
                
        return grouped_files
    except GithubException as e:
        print(f"❌ PR dosyaları alınırken hata oluştu: {e.status} - {e.data}")
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

def generate_tests(prompt):
    """AI modeli kullanarak test kodu üretir."""
    try:
        system_message = """
        Sen bir C++ kütüphanesi geliştiren takımın QA uzmanısın. 
        SimplyECS (Entity Component System) kütüphanesi için unit testler yazıyorsun.
        
        Aşağıdaki kriterlere göre test kodu yazmalısın:
        
        1. GoogleTest kütüphanesini kullan
        2. Kapsamlı test senaryoları oluştur
        3. Edge case'leri test et
        4. Anlaşılır test isimleri ve açıklamaları kullan
        5. Test öncesi kurulum ve sonrası temizlik kodlarını ekle
        
        İstenen görev ve detayları dikkatlice oku, belirtilen C++ koduna uygun testler üret.
        """
        
        response = openai.chat.completions.create(
            model=QA_PERF_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=3000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ AI test üretimi sırasında hata oluştu: {str(e)}")
        return None

def generate_benchmark(prompt):
    """AI modeli kullanarak benchmark kodu üretir."""
    try:
        system_message = """
        Sen bir C++ kütüphanesi geliştiren takımın performans uzmanısın. 
        SimplyECS (Entity Component System) kütüphanesi için benchmark kodları yazıyorsun.
        
        Aşağıdaki kriterlere göre benchmark kodu yazmalısın:
        
        1. Doğru ve tutarlı ölçümler yap
        2. Mikro ve makro benchmarkları içer
        3. Farklı veri büyüklüklerini test et (1K, 10K, 100K, 1M entity)
        4. Sonuçları okunabilir bir formatta raporla
        5. Hedef performansla karşılaştır (1M entity <= 20 ms)
        
        İstenen görev ve detayları dikkatlice oku, belirtilen C++ koduna uygun benchmarklar üret.
        """
        
        response = openai.chat.completions.create(
            model=QA_PERF_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=3000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ AI benchmark üretimi sırasında hata oluştu: {str(e)}")
        return None

def analyze_code(file_contents):
    """Kodu analiz ederek test ve benchmark ihtiyaçlarını belirler."""
    try:
        code_content = "\n\n".join([f"Dosya: {path}\n```cpp\n{content}\n```" 
                                  for path, content in file_contents.items()])
        
        prompt = f"""
        Aşağıdaki C++ kodlarını analiz et ve test/benchmark ihtiyaçlarını belirle:
        
        {code_content}
        
        Analiz sonucunda şunları belirle:
        1. Hangi sınıflar ve fonksiyonlar test edilmeli?
        2. Hangi test senaryoları yazılmalı?
        3. Hangi performans senaryoları ölçülmeli?
        4. Test edilmesi gereken edge case'ler neler?
        5. Hangi benchmark metrikleri ölçülmeli?
        """
        
        response = openai.chat.completions.create(
            model=QA_PERF_MODEL,
            messages=[
                {"role": "system", "content": "Sen bir kod analizi yapan QA uzmanısın."},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=2000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ Kod analizi sırasında hata oluştu: {str(e)}")
        return None

def process_pr():
    """PR'ı işler ve gerekli test/benchmark kodlarını üretir."""
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
        
        # PR'daki dosyaları grupla
        file_groups = get_pr_files(pr)
        if not file_groups:
            print("❌ PR dosyaları alınamadı.")
            return False
        
        # Kod dosyalarını oku
        code_files = {}
        for file_type in ["cpp", "hpp", "inl"]:
            for file_path in file_groups[file_type]:
                content = get_file_content(pr, file_path)
                if content:
                    code_files[file_path] = content
        
        if not code_files:
            print("⚠️ PR'da kod dosyası bulunamadı.")
            return False
        
        print(f"📋 {len(code_files)} kod dosyası bulundu.")
        
        # Kodu analiz et
        code_analysis = analyze_code(code_files)
        if not code_analysis:
            print("❌ Kod analizi başarısız oldu.")
            return False
        
        print("✅ Kod analizi tamamlandı.")
        print(code_analysis)
        
        # Test ve benchmark dosyaları oluştur
        generated_files = []
        
        # Unit testler oluştur
        # Her .hpp dosyası için bir test dosyası oluştur
        for hpp_file in file_groups["hpp"]:
            base_name = os.path.basename(hpp_file).split('.')[0]
            test_file_path = f"tests/{base_name}Tests.cpp"
            
            # Test dosyası zaten var mı kontrol et
            existing_test = None
            for test_file in file_groups["tests"]:
                if os.path.basename(test_file) == f"{base_name}Tests.cpp":
                    existing_test = test_file
                    break
            
            if existing_test:
                print(f"ℹ️ Test dosyası zaten mevcut: {existing_test}")
                continue
            
            # Test kodu üret
            test_prompt = f"""
            Aşağıdaki C++ header dosyası için kapsamlı unit testler yaz:
            
            Header dosyası: {hpp_file}
            ```cpp
            {code_files.get(hpp_file, "// Dosya içeriği alınamadı")}
            ```
            
            Kod analizi:
            {code_analysis}
            
            Test dosyası: {test_file_path}
            GoogleTest kullanarak testleri yaz.
            """
            
            test_code = generate_tests(test_prompt)
            if not test_code:
                print(f"❌ Test kodu üretimi başarısız oldu: {test_file_path}")
                continue
            
            # Test dosyasını oluştur
            commit_message = f"test: add unit tests for {base_name}"
            update_result = update_file(pr, test_file_path, test_code, commit_message)
            
            if update_result:
                print(f"✅ Test dosyası oluşturuldu: {test_file_path}")
                generated_files.append(test_file_path)
        
        # Benchmark dosyası oluştur
        benchmark_file_path = "src/benchmark/ClassBenchmark.cpp"
        
        # Benchmark kodu üret
        benchmark_prompt = f"""
        Aşağıdaki C++ kodları için benchmark testleri yaz:
        
        {chr(10).join([f"Dosya: {path}\n```cpp\n{content}\n```" for path, content in code_files.items()])}
        
        Kod analizi:
        {code_analysis}
        
        Benchmark dosyası: {benchmark_file_path}
        
        SimplyECS performans hedefleri:
        1. 1M entity <= 20 ms
        2. 100K entity @ 60 FPS
        
        Benchmark sonuçlarını konsola yazdır ve geçti/kaldı durumunu raporla.
        """
        
        benchmark_code = generate_benchmark(benchmark_prompt)
        if benchmark_code:
            # Benchmark dosyasını oluştur
            commit_message = "bench: add performance benchmark"
            update_result = update_file(pr, benchmark_file_path, benchmark_code, commit_message)
            
            if update_result:
                print(f"✅ Benchmark dosyası oluşturuldu: {benchmark_file_path}")
                generated_files.append(benchmark_file_path)
        
        # İşlem tamamlandı, PR'a yorum ekle
        comment = f"""
        ## 🧪 QA/Perf Raporu
        
        PR #{PR_NUMBER} için test ve benchmark süreçleri tamamlandı.
        
        **Kod Analizi:**
        ```
        {code_analysis}
        ```
        
        **Oluşturulan Dosyalar:**
        {chr(10).join(['- ' + file for file in generated_files])}
        
        **Performans Hedefleri:**
        - 1M entity ≤ 20 ms
        - 100K entity @ 60 FPS
        
        CI pipeline çalıştırıldığında test ve benchmark sonuçları kontrol edilecek.
        """
        
        pr.create_issue_comment(comment)
        
        # Slack'e bildirim gönder
        notify_slack(f":test_tube: QA/Perf, PR #{PR_NUMBER} için test ve benchmark dosyalarını oluşturdu!")
        
        return len(generated_files) > 0
        
    except Exception as e:
        print(f"❌ PR işlenirken beklenmeyen hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ---------- Ana İş Akışı ----------
def main():
    """QA/Perf'in ana iş akışı."""
    print("🧪 QA/Perf başlatılıyor...")
    
    success = process_pr()
    
    if success:
        print(f"✅ PR #{PR_NUMBER} için test ve benchmark dosyaları başarıyla oluşturuldu.")
        
        # DevOps ekibini tetikle
        print("ℹ️ DevOps ekibini tetikleme işlemi burada yapılacak...")
        # TODO: DevOps ekibini tetikleyen kod eklenecek
    else:
        print(f"❌ PR #{PR_NUMBER} için test ve benchmark dosyaları oluşturulurken hatalar oluştu.")
        
        # Hata durumunda Slack'e bildirim
        notify_slack(f":warning: QA/Perf, PR #{PR_NUMBER} işlenirken sorun yaşadı!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"🔥 QA/Perf'te kritik hata: {str(e)}")
        import traceback
        traceback.print_exc()
        notify_slack(f":boom: QA/Perf'te kritik hata: {str(e)}")
    finally:
        print("🏁 QA/Perf tamamlandı.")