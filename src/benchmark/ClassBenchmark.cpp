```cpp
// File: src/benchmark/ClassBenchmark.cpp
// Author: Performance Team
// Description: Benchmark tests for ecs::World MVP stage (default ctor & dtor).
// Measures construction/destruction time over multiple iterations and reports summary.
// Since currently World has minimal functionality, focus on measuring creation/destruction overhead.

#include <chrono>
#include <iostream>
#include <vector>
#include <string>
#include <iomanip>
#include <memory>
#include <cassert>

#include "ecs/World.h"

using namespace ecs;
using namespace std::chrono;

// Simple RAII timer to measure elapsed time in milliseconds
class ScopedTimer {
public:
    ScopedTimer() : start_(high_resolution_clock::now()) {}
    void reset() { start_ = high_resolution_clock::now(); }
    double elapsedMs() const {
        return duration<double, std::milli>(high_resolution_clock::now() - start_).count();
    }
private:
    time_point<high_resolution_clock> start_;
};

struct BenchmarkResult {
    std::string testName;
    std::size_t iterations;
    double totalMs;
    double avgMs;
    bool passed;
};

class WorldBenchmark {
public:
    WorldBenchmark() = default;

    // Microbenchmark: create & destroy a single World N times, measure cumulative & avg times
    BenchmarkResult benchmarkCreateDestroy(std::size_t iterations) {
        BenchmarkResult result;
        result.testName = "World Create/Destroy (" + std::to_string(iterations) + " iterations)";
        result.iterations = iterations;

        ScopedTimer timer;

        for(std::size_t i = 0; i < iterations; ++i) {
            World w;
            (void)w; // avoid unused variable warning
        }
        result.totalMs = timer.elapsedMs();
        result.avgMs = result.totalMs / (double)iterations;

        // For MVP, assume creation+destruction per World should be < 0.5 ms (arbitrary small threshold)
        result.passed = (result.avgMs < 0.5);

        return result;
    }

    // Macro benchmark: simulate entity count indirectly by constructing/destroying multiple Worlds in parallel
    // Since World has no entity management yet, just measure create/destroy times for different batch sizes.
    BenchmarkResult benchmarkMultipleWorlds(std::size_t worldCount) {
        BenchmarkResult result;
        result.testName = "Bulk World Create/Destroy (" + std::to_string(worldCount) + " Worlds)";
        result.iterations = 1;

        ScopedTimer timer;
        {
            // Vector of unique_ptr to Worlds to ensure delayed destruction all at once
            std::vector<std::unique_ptr<World>> worlds;
            worlds.reserve(worldCount);

            for(std::size_t i = 0; i < worldCount; ++i) {
                worlds.emplace_back(std::make_unique<World>());
            }
            // Worlds destroyed here when vector goes out of scope
        }
        result.totalMs = timer.elapsedMs();
        result.avgMs = result.totalMs / (double)worldCount;

        // Passing criteria: For a single World > 0.5ms is fail (arbitrary small threshold)
        result.passed = (result.avgMs < 0.5);

        return result;
    }

    // Since no entities or components exist yet, simulate timing for future API placeholders at different sizes.
    // Stub for 1K, 10K, 100K, 1M entity scenario benchmarks as place holders.
    void benchmarkPlaceHolderEntities(std::size_t entityCount) {
        std::cout << "Benchmark placeholder for " << entityCount << " entities. (MVP stage - no operation)\n";
    }

    void runAll() {
        std::cout << "=== SimplyECS World Class Benchmark (MVP-stage) ===\n\n";

        // Microbenchmark: single World create/destroy repeated 100k times
        auto micro = benchmarkCreateDestroy(100'000);
        printResult(micro);

        // Macro benchmark: bulk create/destroy Worlds - testing 1K, 10K Worlds to simulate scale
        auto bulk1k = benchmarkMultipleWorlds(1'000);
        printResult(bulk1k);

        auto bulk10k = benchmarkMultipleWorlds(10'000);
        printResult(bulk10k);

        // Placeholder benchmarks for entity sizes - no operation yet
        const std::size_t sizes[] = {1'000, 10'000, 100'000, 1'000'000};
        for(auto size : sizes)
            benchmarkPlaceHolderEntities(size);

        std::cout << "\n=== Summary ===\n";
        printPassFail(micro);
        printPassFail(bulk1k);
        printPassFail(bulk10k);

        std::cout << "\nBenchmark complete.\n";
    }

private:

    void printResult(const BenchmarkResult& res) {
        std::cout <<
            std::left << std::setw(40) << res.testName <<
            "Total: " << std::fixed << std::setprecision(3) << res.totalMs << " ms, " <<
            "Avg: " << res.avgMs << " ms per iteration, " <<
            "Result: " << (res.passed ? "PASS" : "FAIL") << "\n";
    }

    void printPassFail(const BenchmarkResult& res) {
        std::cout << res.testName << ": " << (res.passed ? "[PASS]" : "[FAIL]") << "\n";
    }
};

int main() {
    // Run the benchmark suite for ecs::World MVP
    WorldBenchmark bench;
    bench.runAll();

    return 0;
}
```

---

### Açıklamalar:

- `World` sınıfının şu anki hali sadece varsayılan constructor ve destructor içerdiğinden benchmark testleri öncelikle bu çağrıların CPU süresi ve bellek oynanımı açısından çok hızlı olduğunu doğrulamak içindir.
  
- **Mikro benchmark:** `benchmarkCreateDestroy` fonksiyonu, tek bir `World` nesnesinin oluşturulup yok edilmesi süresini 100.000 kez ölçerek "ortalama süre" çıkarır. Küçük bir seuild (örneğin 0.5 ms) geçilmemelidir.

- **Makro benchmark:** `benchmarkMultipleWorlds` fonksiyonu, örneğin 1000 veya 10,000 `World` nesnesini ardışık olarak yaratır ve tek seferde yok eder. Böylece büyük hacimlerdeki işlemler test edilir.

- Henüz `World` içinde entity ya da component yönetimi yok. Bu yüzden bu benchmark'lar temel oluşturur. İleride eklenecek fonksiyonlarla birlikte daha kapsamlı benchmark hazırlanmalıdır.

- Konsola raporlama, okunabilir sütunlar ve formata uygun.

- Performans hedefleri (örneğin 1M entity <= 20 ms) bu aşamada uygulanmadı çünkü `World` sınıfı yaratma/yok etme ile entity yönetimi fonksiyonları yok.

- Stres testi olarak çok sayıda `World` nesnesi örnekleniyor ki ileride çok sayıda entity içeren World performansı ölçülmeye hazır olsun.

- Bellek sızıntısı, tasarım gereği, bu benchmark çalıştığında valgrind/memcheck gibi araçlar ile ayrıca kontrol edilmelidir.

---

Bu benchmark kodunu projenizin uygun build sistemiyle derleyip çalıştırarak `ecs::World` temel performans kriterlerini test edip takip edebilirsiniz. İleride fonksiyonlar eklendikçe benchmark dosyasını genişletiniz.