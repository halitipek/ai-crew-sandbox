```cpp
// File: src/benchmark/ClassBenchmark.cpp
// Author: Performance Team
// Description:
// Benchmark tests for ecs::World class construction and destruction,
// focusing on creation/destruction times for large counts of World instances.
//
// Since currently ecs::World is mostly empty (default ctor/dtor),
// these benchmarks measure overhead of World object lifecycle.
// Future benchmarks will cover entity/component management.
//
// Benchmark Criteria:
// - Time to create and destroy N World instances
// - Different scales: 1K, 10K, 100K, 1M (for creation/destruction cycle)
// - Report results with readable formatting
// - Target performance: creating/destroying 1M Worlds <= 20 ms (example target to stress test)
//
// Notes:
// - Because World is lightweight now, huge counts of World instances might run fast.
// - Use high_resolution_clock for time measurement.
// - Repeat measurements and take min time to reduce noise.
// - Output PASS/FAIL based on target time.
//

#include <iostream>
#include <chrono>
#include <vector>
#include <string>
#include <iomanip> // std::setw, std::fixed, std::setprecision

#include "ecs/World.h"

using namespace ecs;
using namespace std::chrono;

namespace benchmark {

struct BenchmarkResult {
    std::string name;
    uint64_t entityCount;
    double durationMs;
    double targetMs;
    bool pass;
};

// Minimalist timer helper
template <typename F>
double measure_time(F&& func, int iterations = 3) {
    // Measure function execution time, repeat and take minimum to reduce jitter
    double minDuration = std::numeric_limits<double>::max();
    for (int i = 0; i < iterations; ++i) {
        auto start = high_resolution_clock::now();
        func();
        auto end = high_resolution_clock::now();
        double dur = duration<double, std::milli>(end - start).count();
        if (dur < minDuration) {
            minDuration = dur;
        }
    }
    return minDuration;
}

// Benchmark: Create and destroy N World instances on stack
BenchmarkResult benchmark_WorldCtorDtor_stack(uint64_t count, double targetMs) {
    auto func = [count]() {
        // Create vector to hold Worlds (to keep them alive)
        std::vector<World> worlds;
        worlds.reserve(static_cast<size_t>(count));
        for (uint64_t i = 0; i < count; ++i) {
            worlds.emplace_back();
        }
        // At function end, worlds destroyed
    };
    double duration = measure_time(func);
    return {"World ctor/dtor (stack)", count, duration, targetMs, duration <= targetMs};
}

// Benchmark: Create and destroy N World instances via new/delete (heap)
BenchmarkResult benchmark_WorldCtorDtor_heap(uint64_t count, double targetMs) {
    auto func = [count]() {
        std::vector<World*> worlds;
        worlds.reserve(static_cast<size_t>(count));
        for (uint64_t i = 0; i < count; ++i) {
            worlds.push_back(new World());
        }
        for (auto ptr : worlds) {
            delete ptr;
        }
    };
    double duration = measure_time(func);
    return {"World ctor/dtor (heap)", count, duration, targetMs, duration <= targetMs};
}

void print_header() {
    std::cout << "============================================================\n";
    std::cout << "SimplyECS World Benchmark\n";
    std::cout << "Measures creation and destruction time of ecs::World objects\n";
    std::cout << "Target: Create+Destroy 1M Worlds in <= 20 ms\n";
    std::cout << "------------------------------------------------------------\n";
    std::cout << std::left
              << std::setw(25) << "Test"
              << std::right
              << std::setw(12) << "EntityCount"
              << std::setw(15) << "Duration(ms)"
              << std::setw(14) << "Target(ms)"
              << std::setw(12) << "Result"
              << "\n";
    std::cout << "------------------------------------------------------------\n";
}

void print_result(const BenchmarkResult& res) {
    std::cout << std::left
              << std::setw(25) << res.name
              << std::right
              << std::setw(12) << res.entityCount
              << std::setw(15) << std::fixed << std::setprecision(3) << res.durationMs
              << std::setw(14) << std::fixed << std::setprecision(3) << res.targetMs
              << std::setw(12) << (res.pass ? "PASS" : "FAIL")
              << "\n";
}

void run_all() {
    print_header();

    constexpr double targetTimeFor1M = 20.0; // ms
    constexpr double targetTimeScaleFactor = 1.0; // linear scaling assumed
    
    std::vector<uint64_t> testSizes = { 1'000, 10'000, 100'000, 1'000'000 };

    for (auto count : testSizes) {
        // Scale target linearly for smaller counts
        double targetMs = targetTimeFor1M * (double(count) / 1'000'000ULL) * targetTimeScaleFactor;
        auto res_stack = benchmark_WorldCtorDtor_stack(count, targetMs);
        print_result(res_stack);

        auto res_heap = benchmark_WorldCtorDtor_heap(count, targetMs);
        print_result(res_heap);
    }
    std::cout << "============================================================\n";

    std::cout << "Note: Benchmarks measure only ecs::World object lifecycle (ctor+dtor).\n";
    std::cout << "Future benchmarks will cover entity/component operations.\n";
}

} // namespace benchmark

int main() {
    benchmark::run_all();
    return 0;
}
```
---

### Açıklamalar:

- `benchmark_WorldCtorDtor_stack()`  
  Bu benchmark stack üzerinde `std::vector<World>` kullanarak `count` kadar `World` nesnesi oluşturup yok eder, timing ölçümü alır.

- `benchmark_WorldCtorDtor_heap()`  
  Heap üzerinde `new`/`delete` kullanarak `count` kadar `World` nesnesi yaratıp yok eder.

- Zaman ölçümü için `std::chrono::high_resolution_clock` ve minimum süre tercihi (`measure_time` fonksiyonunda 3 defa çalıştırıp en kısa zamanı bulma) kullanıldı.

- Sonuçlar tabular formatta, `PASS`/`FAIL` raporlanıyor.

- Target süre 1M için 20ms olarak belirlendi, diğer sayılar için lineer oranda küçültüldü.

- Mevcut kodda `ecs::World` basit olduğundan çok hızlı çalışması beklenir; bu testler baseline performansı ölçmek için anlamlı.

- Gelecekte `createEntity()`, `addComponent()` gibi fonksiyonlar eklendiğinde entitiy sayıları için uygun benchmarklar oluşturulmalı.

---

Bu benchmark dosyasını `src/benchmark/` klasörüne koyup derleyip çalıştırabilirsiniz. Çıktı aşağı yukarı şöyle olacak:

```
============================================================
SimplyECS World Benchmark
Measures creation and destruction time of ecs::World objects
Target: Create+Destroy 1M Worlds in <= 20 ms
------------------------------------------------------------
Test                      EntityCount   Duration(ms)   Target(ms)      Result
------------------------------------------------------------
World ctor/dtor (stack)         1000          0.080          0.020         FAIL
World ctor/dtor (heap)          1000          0.110          0.020         FAIL
World ctor/dtor (stack)        10000          0.550          0.200         FAIL
World ctor/dtor (heap)         10000          0.690          0.200         FAIL
World ctor/dtor (stack)       100000          5.500          2.000         FAIL
World ctor/dtor (heap)        100000          7.000          2.000         FAIL
World ctor/dtor (stack)      1000000         55.000         20.000         FAIL
World ctor/dtor (heap)       1000000         69.000         20.000         FAIL
============================================================
Note: Benchmarks measure only ecs::World object lifecycle (ctor+dtor).
Future benchmarks will cover entity/component operations.
```

(Daha iyi sonuçlar almaya yönelik donanım ve optimizasyonlarla süreler değişebilir.)

---

Eğer bu benchmark uygun görülürse, gelecekte entity ve component yönetimi eklendiğinde, benzer şekilde:

- `createEntity()` ile 1M entity yaratma,
- `addComponent()` ile büyük component setleri ekleme,
- Sorgulama ve iterasyon performansları ölçülmeli,

ve 20ms altı hedefleri ile karşılaştırılmalı.