```cpp
// File: src/benchmark/ClassBenchmark.cpp
// Author: ECS Performance Team
// Description:
//   Micro & Macro benchmarks for ecs::World MVP-1 (default ctor/dtor).
//   Measures construction/destruction latency of World instances,
//   over different iteration counts and entity-size simulated workloads.
//
//   Current ECS MVP has no entity/component functions yet, so benchmarks
//   focus on ctor/dtor overhead and scalability for large loads.
//   Results are output to console with timing and pass/fail against
//   SimplyECS performance goals for future reference.
//
// Usage:
//   Build with optimization enabled (-O2 or -O3).
//   Run in release mode to minimize noise.
//
// Note:
//   Future benchmarks will cover createEntity/addComponent etc.
//

#include <chrono>
#include <iostream>
#include <vector>
#include <string>
#include <iomanip>
#include <exception>
#include <thread>

#include "ecs/World.h"

using Clock = std::chrono::steady_clock;
using namespace std::chrono;

namespace {

struct BenchmarkResult {
    std::string name;
    size_t entityCount;    // Simulated entities (for future use)
    size_t iterations;
    double timeMs;
    bool passed;
};

// Simple helper to simulate workload per entity (no-op here)
inline void simulateEntityWork(size_t /*entityCount*/) {
    // MVP-1 has no entities yet; placeholder for future loads
}

BenchmarkResult benchmarkWorldConstructionDestruction(size_t entityCount, size_t iterations) {
    // Measure total time to construct & destruct "iterations" Worlds
    // entityCount only for reporting right now.

    using clock = Clock;
    volatile ecs::World* volatile ptr = nullptr; // prevent optimization

    auto start = clock::now();

    try {
        for (size_t i = 0; i < iterations; ++i) {
            ecs::World* w = new ecs::World();
            simulateEntityWork(entityCount);
            delete w;
        }
    } catch (const std::exception& ex) {
        std::cerr << "[ERROR] Exception during benchmark: " << ex.what() << std::endl;
        return {"WorldCtorDtor", entityCount, iterations, -1.0, false};
    } catch (...) {
        std::cerr << "[ERROR] Unknown exception during benchmark." << std::endl;
        return {"WorldCtorDtor", entityCount, iterations, -1.0, false};
    }

    auto end = clock::now();
    double elapsedMs = duration_cast<duration<double, std::milli>>(end - start).count();

    // Pass conditions:
    // For 1M entities: total time (all iterations) <= 20 ms evolving goal
    // Since we do multiple iterations, we compare average creation/destruction time * entityCount
    // As MVP has no ECS data, just check total time under a scaled budget:
    //
    // We'll consider "entityCount" as a workload proxy for future versions,
    // so time should linearly scale or be negligible here.

    bool pass = true;
    if (entityCount == 1000000) {
        // Entire benchmark should be <= 20 ms total to meet goal
        pass = elapsedMs <= 20.0;
    } else if (entityCount == 100000) {
        // Relax for 100K entities benchmark (target around few ms)
        pass = elapsedMs <= 10.0;
    } else if (entityCount == 1000) {
        pass = elapsedMs <= 1.0;
    } else if (entityCount == 0) {
        // microbenchmark with zero entities, just ctor/dtor overhead:
        pass = elapsedMs <= 5.0;
    }

    return BenchmarkResult{"WorldCtorDtor", entityCount, iterations, elapsedMs, pass};
}

// Run all benchmarks with different entity counts and iteration counts
std::vector<BenchmarkResult> runBenchmarks() {
    std::vector<BenchmarkResult> results;

    // We run 3 different entity counts, simulating future entity workload size:
    std::vector<size_t> entityCounts = {1000, 100000, 1000000};
    std::vector<size_t> iterations = {10000, 100, 10};

    for (size_t i = 0; i < entityCounts.size(); ++i) {
        size_t entities = entityCounts[i];
        size_t iter = iterations[i];
        auto res = benchmarkWorldConstructionDestruction(entities, iter);
        results.push_back(res);
    }

    // Also add a micro benchmark: many ctor/dtor with zero entities
    results.push_back(benchmarkWorldConstructionDestruction(0, 100000));

    return results;
}

void reportResults(const std::vector<BenchmarkResult>& results) {
    std::cout << "======================================" << std::endl;
    std::cout << "SimplyECS World MVP-1 Benchmark Report" << std::endl;
    std::cout << "Date: " << __DATE__ << " " << __TIME__ << std::endl;
    std::cout << "--------------------------------------" << std::endl;

    std::cout << std::left << std::setw(20) << "Test"
              << std::setw(15) << "Entities"
              << std::setw(12) << "Iterations"
              << std::setw(12) << "Time (ms)"
              << std::setw(10) << "Status"
              << std::endl;

    std::cout << "--------------------------------------" << std::endl;

    for (auto& res : results) {
        std::cout << std::left << std::setw(20) << res.name
                  << std::setw(15) << res.entityCount
                  << std::setw(12) << res.iterations
                  << std::setw(12) << std::fixed << std::setprecision(3) << res.timeMs
                  << std::setw(10) << (res.passed ? "PASS" : "FAIL")
                  << std::endl;
    }

    std::cout << "--------------------------------------" << std::endl;

    // Summary
    size_t passedCount = 0;
    for (auto& r : results) if (r.passed) ++passedCount;

    std::cout << "Summary: " << passedCount << " / " << results.size() << " benchmarks passed." << std::endl;

    if (passedCount != results.size()) {
        std::cout << "[WARNING] Some benchmarks did not meet the target times." << std::endl;
        std::cout << "Targets:" << std::endl;
        std::cout << "  1M entities <= 20 ms total for creation + destruction" << std::endl;
        std::cout << "  100K entities benchmark aims < 10 ms" << std::endl;
        std::cout << "  1K entities benchmark aims < 1 ms" << std::endl;
    } else {
        std::cout << "[INFO] All benchmarks passed performance targets." << std::endl;
    }
    std::cout << "======================================" << std::endl;
}

} // anonymous namespace

int main() {
    std::cout << "[INFO] Starting SimplyECS World MVP-1 benchmarks..." << std::endl;

    auto results = runBenchmarks();

    reportResults(results);

    return 0;
}
```

---

# Açıklamalar ve Notlar

- `World` sınıfı henüz işlevsellik içermediği için benchmark sadece oluşturma ve yok etme sürelerini ölçüyor.
- Gelecekte entity ve component fonksiyonları eklenince benchmarklar kolayca genişletilebilir.
- Performans hedeflerine göre 1M entity için toplam ctor+dtor süresi 20 ms altında olmalı.
- İterasyonlar entity sayısına göre ayarlanmıştır (çok entity az iterasyon, az entity çok iterasyon).
- `simulateEntityWork` fonksiyonu şimdilik boş, gelecekte entity başına işlem eklenebilir.
- Sonuçlar tablo formatında ve anlaşılır şekilde raporlanır.
- Hata durumları yakalanır ve bildirilir.
- Benchmarklar seri çalışır, çoklu thread testi ileride eklenmeli.
- Kod C++11+ uyumludur (chrono, nullptr, otomatik tipi çıkarımı kullanımı).
- Testleri release modda çalıştırmak önerilir.
- Gelişmiş bellek ölçümü ve fragmentasyon testleri ileride eklenecek.

---

İsterseniz sonraki aşamada entity/component fonksiyonları eklendiğinde detaylı işlevsel ve performans testlerini içeren benchmarklar üretilebilir. Şimdilik bu kod temel yapıcı-yıkıcı benchmark olarak görev yapacaktır.