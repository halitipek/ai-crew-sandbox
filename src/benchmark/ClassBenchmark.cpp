```cpp
// File: src/benchmark/ClassBenchmark.cpp
// Benchmark tests for ecs::World default constructor and destructor.
//
// This benchmark primarily measures the cost of creating and destroying
// World objects, especially focusing on large scale scenarios for future baseline.
//
// Since ecs::World currently has only default ctor/dtor with no entity/component logic,
// the benchmark tests focus on instance lifecycle and memory overhead.
//
// Target performance:
// - Creating/destroying a World with simulated large entity counts (conceptual, as no entities yet)
// - Baseline for future comparison when entities/components are implemented.
//
// Format:
// - Run measurements for 1K, 10K, 100K, 1M "entities" (simulated as repeated ctor/dtor or allocated objects)
// - Report times in milliseconds
// - Check if 1M entity scenario <= 20 ms (current code trivial, should pass easily)
//
// Dependencies:
// - C++11 chrono
// - iostream
//

#include <chrono>
#include <iostream>
#include <vector>
#include <string>
#include <iomanip>

#include "ecs/World.h"

using namespace ecs;
using Clock = std::chrono::high_resolution_clock;

struct BenchmarkResult {
    std::string testName;
    size_t entityCount;    // number of simulated entities
    double durationMs;     // elapsed time in milliseconds
    bool passed;
};

void runBenchmarkCtorDtor(size_t entityCount, BenchmarkResult& result) {
    // This benchmark simulates the cost of creating and destroying World objects.
    // Since World currently does NOT manage entities internally, we simulate "entityCount"
    // by creating/destroying the World instance repeatedly "entityCount" times.
    //
    // This is admittedly artificial but provides a baseline.
    //
    // In the future, when World manages entities, this test will 
    // directly create 1K..1M entities and measure.
    //
    auto start = Clock::now();

    for(size_t i = 0; i < entityCount; ++i) {
        World w;
        // minimal scope to call ctor then dtor on destruction
    }

    auto end = Clock::now();
    double elapsedMs = std::chrono::duration<double, std::milli>(end - start).count();

    result.testName = "World ctor/dtor x N";
    result.entityCount = entityCount;
    result.durationMs = elapsedMs;

    // Target: For 1M "entities" simulated, <= 20ms
    if(entityCount == 1000000) {
        result.passed = (elapsedMs <= 20.0);
    } else {
        // For smaller runs no target, assume pass
        result.passed = true;
    }
}

void printBenchmarkResult(const BenchmarkResult& res) {
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "[Benchmark] " << res.testName << "\n"
              << "  Entity Count: " << res.entityCount << "\n"
              << "  Duration:     " << res.durationMs << " ms\n"
              << "  Result:       " << (res.passed ? "PASS" : "FAIL") << "\n"
              << std::endl;
}

int main() {
    std::cout << "SimplyECS World ctor/dtor benchmark\n";
    std::cout << "-----------------------------------\n";
    std::cout << "Target for 1M entities: <= 20 ms\n\n";

    const size_t testEntityCounts[] = {1000, 10000, 100000, 1000000};
    std::vector<BenchmarkResult> results;

    for(size_t count : testEntityCounts) {
        BenchmarkResult res;
        runBenchmarkCtorDtor(count, res);
        printBenchmarkResult(res);
        results.push_back(res);
    }

    // Summary report
    size_t passCount = 0;
    for(const auto& r : results) {
        if(r.passed) ++passCount;
    }

    std::cout << "Summary: Passed " << passCount << " / "
              << results.size() << " benchmarks.\n";

    if(passCount == results.size()) {
        std::cout << "Overall Result: SUCCESS\n";
        return 0; // success
    } else {
        std::cout << "Overall Result: FAILURE\n";
        return 1; // failure
    }
}
```

---

### Açıklama ve öneriler:

- Şu anki ecs::World sadece ctor/dtor barındırdığı için gerçek entity oluşturma benchmarkları yapılamıyor.
- Performans ölçümü amacıyla World objesini N defa oluşturup yok ederek (simüle edilerek) test yapıldı.
- Gerçek kullanımda entity sayısına göre (örn. 1M entity) create/destroy fonksiyonları benchmark edilince gerçek test yapılacaktır.
- Test sonuçlarını ms cinsinden çıktı olarak veriyor, performans hedefi 1M entity için 20ms olarak konuldu.
- Küçük entity sayıları (1K,10K,100K) için anlamlı geçme ölçütü koymadım çünkü trivial.

İleride `ecs::World` sınıfına entity ve component fonksiyonları eklendiğinde, mutlaka bu benchmark dosyasında:

- entity create/destroy hızları,
- component ekleme/erişim hızları,
- memory usage ölçümleri,
- concurrency benchmarkları

gibi kapsamlı ve gerçekçi performans testleri yapılmalıdır.

---

İyi çalışmalar!