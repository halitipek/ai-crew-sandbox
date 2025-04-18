```cpp
// File: src/benchmark/ClassBenchmark.cpp
// Description: Benchmark tests for ecs::World class (constructor & destructor).
// Author: SimplyECS Performance Team
//
// Measures performance of creating and destroying ecs::World instances,
// simulating micro and macro benchmarks for different scales.

#include <iostream>
#include <vector>
#include <chrono>
#include "ecs/World.h"

// UTILITIES

using Clock = std::chrono::high_resolution_clock;
using DurationMs = std::chrono::duration<double, std::milli>;

// Print separator line
void printSeparator() {
    std::cout << "--------------------------------------------\n";
}

// Report benchmark result and pass/fail based on threshold
void reportResult(const std::string& testName, double timeMs, double targetMs) {
    std::cout << testName << ": " << timeMs << " ms";
    if (targetMs > 0.0) {
        if (timeMs <= targetMs) {
            std::cout << " [PASS] (<= " << targetMs << " ms)\n";
        } else {
            std::cout << " [FAIL] (> " << targetMs << " ms)\n";
        }
    } else {
        std::cout << '\n';
    }
}

// Benchmark: create and destroy single World instance (micro benchmark)
double benchmarkSingleWorldCreateDestroy(size_t iterations = 100000) {
    using namespace ecs;
    auto start = Clock::now();
    for (size_t i = 0; i < iterations; ++i) {
        World w;
        (void)w; // suppress unused warning
    }
    auto end = Clock::now();
    DurationMs duration = end - start;
    return duration.count() / iterations; // average per create/destroy in ms
}

// Benchmark: create and destroy multiple World instances in batch (macro benchmark)
double benchmarkBatchWorldCreateDestroy(size_t instances) {
    using namespace ecs;
    std::vector<World> worlds;
    worlds.reserve(instances);

    auto start = Clock::now();
    for (size_t i = 0; i < instances; ++i) {
        worlds.emplace_back(); // create
    }
    worlds.clear(); // destroy all
    auto end = Clock::now();
    DurationMs duration = end - start;
    return duration.count();
}

// Simulate rapid create/destroy in tight loop for given count
double benchmarkRapidCreateDestroyLoop(size_t loopCount) {
    using namespace ecs;
    auto start = Clock::now();
    for (size_t i = 0; i < loopCount; ++i) {
        {
            World w;
            (void)w;
        } // immediate destruction at scope end
    }
    auto end = Clock::now();
    DurationMs duration = end - start;
    return duration.count();
}

// Test multiple World instances lifetime overlap and destruction
bool testMultipleInstanceLifecycle() {
    using namespace ecs;
    try {
        World w1, w2;
        // Normally would check internal states here if they existed
        // Test passes if no crash or exception
        return true;
    } catch (...) {
        return false;
    }
}

// MAIN BENCHMARK FUNCTION
int main() {
    using namespace std;

    cout << "SimplyECS World class - Constructor & Destructor Benchmark\n";
    printSeparator();

    // MICRO BENCHMARK: Single instance create/destroy
    constexpr size_t microIters = 100000;
    double microAvgMs = benchmarkSingleWorldCreateDestroy(microIters);
    reportResult("Microbenchmark - Single World create/destroy (avg per instance)", microAvgMs, 0.1);
    // No strict target here, just checking triviality (~few microseconds expected)

    printSeparator();

    // MACRO BENCHMARK: Batch create/destroy for large counts
    // Since World currently trivial, time will be near zero but measured anyway.
    const vector<size_t> testSizes = { 1000, 10000, 100000 }; // 1K, 10K, 100K entities simulated
    for (size_t count : testSizes) {
        // Target scaling - no precise target (World create/destroy trivial), but display times
        double totalMs = benchmarkBatchWorldCreateDestroy(count);
        cout << "Macrobenchmark - Create & destroy " << count << " World instances: "
             << totalMs << " ms\n";
    }

    printSeparator();

    // RAPID CREATE/DESTROY LOOP: simulate short lifespan object churn
    constexpr size_t rapidLoopCount = 1000000;
    double rapidLoopMs = benchmarkRapidCreateDestroyLoop(rapidLoopCount);
    cout << "Rapid create/destroy in loop (1M times): " << rapidLoopMs << " ms\n";

    printSeparator();

    // MULTIPLE INSTANCE LIFECYCLE TEST (functional correctness - no crash)
    bool multiInstanceOk = testMultipleInstanceLifecycle();
    cout << "Multiple World instances creation/destruction test: "
         << (multiInstanceOk ? "[PASS]" : "[FAIL]") << '\n';

    printSeparator();

    // SUMMARY related to SimplyECS 1M entities target (<=20 ms)
    // Here World class only default ctor/dtor, no entity management yet.
    // So benchmark simulating 1M calls (create/destroy) to World as proxy:
    constexpr size_t oneMillion = 1'000'000;
    double oneMTotalMs = benchmarkBatchWorldCreateDestroy(oneMillion);
    cout << "Create & destroy 1M World instances total time: " << oneMTotalMs << " ms\n";

    constexpr double target1M = 20.0; // target in ms according to spec
    if (oneMTotalMs <= target1M) {
        cout << "[PERFORMANCE TARGET PASSED] (<= " << target1M << " ms)\n";
    } else {
        cout << "[PERFORMANCE TARGET FAILED] (> " << target1M << " ms)\n";
    }

    printSeparator();

    cout << "Benchmark completed.\n";

    return 0;
}
```
---

### Açıklamalar

- **Mikro benchmark** olarak, `ecs::World` objesinin tek tek yaratılması ve yok edilmesi ortalama süresi ölçülüyor (100K iterasyon).
- **Makro benchmark** farklı sayılarda (1K, 10K, 100K) `World` nesnesinin toplu oluşturulup yok edilme süreleri ölçülüyor.
- 1M instance yaratılıp yok edilerek hedef performans (20 ms toplam) test ediliyor.
- Çok hızlı ardışık yaratıp yok etme (1M adım) testi yapılmakta.
- Çoklu nesne yaratıp yok etme fazlalığı sırasında sistemin stabil (crash olmadan) çalıştığı test ediliyor.
- Raporlar konsola yazdırılıyor, basit geçme/kalmaya göre hedefler kontrol ediliyor.
- Kodda gerçek entity veya component olmadığı için gerçek 1M entity benchmarkı yapılamıyor, bu benchmarklar ileride genişletilecek.

---

### Çalıştırma Notları

- Kod standart C++17 ve üstü ile uyumludur.
- `ecs::World` sınıfınız build edilip bu benchmark ile linklenmelidir.
- Benchmark sonuçları donanım ve derleyiciye göre değişebilir.
- Bu baseline ölçümler ileriki ECS özellikleri eklendikçe zenginleştirilecek.
- Daha gelişmiş isterseniz Google Benchmark kütüphanesi entegre edilebilir.

---

Başarılar ve kolay gelsin!  
SimplyECS Performans Ekibi