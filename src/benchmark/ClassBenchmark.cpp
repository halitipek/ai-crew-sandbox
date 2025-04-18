```cpp
// File: src/benchmark/ClassBenchmark.cpp
// Benchmark for ecs::World constructor and destructor.
// Since World currently is MVP (only default ctor/dtor),
// we focus on creation/destruction overhead and stability.
//
// Benchmark scenarios:
// - Create and destroy multiple World instances in batch.
// - Test scalability with batch sizes: 1K, 10K, 100K, 1M Worlds.
// - Measure average time per create/destroy.
// - Validate no crashes and report times.
//
// NOTE:
// Currently no entity/component management exists,
// so we benchmark World instance lifecycle only.
//
// Usage:
// Compile with optimization, e.g. -O2 -std=c++17
// Run and observe output.

#include <chrono>
#include <iostream>
#include <vector>
#include <string>
#include <iomanip> // setw, setprecision

#include "ecs/World.h"

using Clock = std::chrono::steady_clock;

struct BenchmarkResult {
    size_t count;
    double total_ms;
    double avg_us; // average us per World create/destroy pair
    bool passed;
};

void benchmarkWorldLifecycle(size_t worldCount, BenchmarkResult& result) {
    // Measure time to create and destroy `worldCount` World instances sequentially.
    // Allocate vector on heap to avoid stack overflow in very large tests.
    std::vector<ecs::World*> worlds;
    worlds.reserve(worldCount);

    auto start = Clock::now();

    for (size_t i = 0; i < worldCount; ++i) {
        worlds.push_back(new ecs::World());
    }

    for (ecs::World* w : worlds) {
        delete w;
    }
    worlds.clear();

    auto end = Clock::now();
    std::chrono::duration<double, std::milli> elapsed = end - start;

    result.count = worldCount;
    result.total_ms = elapsed.count();
    result.avg_us = (elapsed.count() * 1000.0) / worldCount;
    // Performance criteria meaningful only for large counts (simulate entity count)
    // Target: for 1M world creations <= 20ms (same limit as entities)
    if (worldCount == 1000000) {
        result.passed = (elapsed.count() <= 20.0);
    } else if (worldCount == 100000) {
        // For 100K entities 16.66 ms <= 1 frame at 60fps, less strict
        result.passed = (elapsed.count() <= 33.0);
    } else {
        // For smaller counts just pass
        result.passed = true;
    }
}

void printHeader() {
    std::cout << "SimplyECS World Lifecycle Benchmark\n";
    std::cout << "===================================\n";
    std::cout << "Tests creation + destruction of ecs::World objects\n";
    std::cout << std::fixed << std::setprecision(3);
    std::cout << std::setw(12) << "Instances" 
              << std::setw(15) << "Total Time(ms)" 
              << std::setw(20) << "Avg Time per instance(us)"
              << std::setw(12) << "Status\n";
    std::cout << "-------------------------------------------------------------------------------\n";
}

void printResult(const BenchmarkResult& res) {
    std::cout << std::setw(12) << res.count 
              << std::setw(15) << res.total_ms 
              << std::setw(20) << res.avg_us
              << std::setw(12) << (res.passed ? "Passed" : "Failed") << "\n";
}

int main() {
    printHeader();

    constexpr size_t counts[] = {1000, 10000, 100000, 1000000};
    bool global_pass = true;

    for (size_t c : counts) {
        BenchmarkResult res{};
        benchmarkWorldLifecycle(c, res);
        printResult(res);
        if (!res.passed) global_pass = false;
    }

    std::cout << "===================================\n";
    if (global_pass) {
        std::cout << "All benchmarks passed SimplyECS performance targets.\n";
    } else {
        std::cout << "Some benchmarks FAILED performance targets.\n";
        std::cout << "Note: Current World class is MVP skeleton, no entity management.\n";
    }

    return global_pass ? 0 : 1;
}
```

---

### Açıklamalar

- **Benchmark amacı:** `ecs::World` objelerinin oluşturulma ve yok edilme süresini ölçmek.
- **Senaryolar:** 1K, 10K, 100K, 1M adet `World` objesi yaratılıp yok ediliyor.
- **Performans Hedefleri:**
  - 1M objenin oluşturulup yok edilmesi ≤ 20 ms (aynı entity hedefi ile),  
  - 100K objenin ≤ 33 ms (esnek 60 FPS sınırına göre).
- **Raporlama:** Konsola tablo şeklinde, okunabilir biçimde çıktı veriliyor.
- **Geçti/Kaldı Durumu:** Zaman hedeflerine göre işaretleniyor ve sonuç özetleniyor.
- **Mimari:** `new/delete` ile dinamik allocated `World` objeleri kullanılıyor. 
  - Yığın taşıma sınırından kaçınmak için bu tercih edildi.
- **Gelecek için:** `World` sınıfının genişletilmesi ile (entity yaratma, component ekleme vb.)
  performans testleri de eklenmelidir.

---

Bu benchmark kodu mevcut haliyle MVP framework için uygundur ve 
şimdilik World yaratma/yok etme maliyetlerini ölçmek ve stabilize etmek için kullanılabilir.