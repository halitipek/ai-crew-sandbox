
```cpp
// File: src/benchmark/ClassBenchmark.cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <memory>
#include <string>
#include <iomanip>

#include "ecs/World.h"

// Utility for printing benchmark headers and results
namespace bench_utils {

using Clock = std::chrono::steady_clock;
using DurationMs = std::chrono::duration<double, std::milli>;

struct BenchmarkResult {
    std::string name;
    size_t entityCount;
    double durationMs;
    bool passed;
};

void printHeader() {
    std::cout << "\n=== SimplyECS Benchmark Results ===\n";
    std::cout << std::left
              << std::setw(25) << "Test"
              << std::setw(12) << "Entities"
              << std::setw(15) << "Duration (ms)"
              << std::setw(10) << "Status"
              << std::endl;
    std::cout << std::string(62, '-') << std::endl;
}

void printResult(const BenchmarkResult& r) {
    std::cout << std::left
              << std::setw(25) << r.name
              << std::setw(12) << r.entityCount
              << std::setw(15) << std::fixed << std::setprecision(3) << r.durationMs
              << (r.passed ? "PASSED" : "FAILED")
              << std::endl;
}

// Runs the given function N times and returns average duration (ms)
template <typename Func>
double benchmarkAverage(Func&& func, size_t runs = 5) {
    std::vector<double> durations;
    durations.reserve(runs);
    for (size_t i = 0; i < runs; ++i) {
        auto start = Clock::now();
        func();
        auto end = Clock::now();
        auto diff = std::chrono::duration_cast<DurationMs>(end - start);
        durations.push_back(diff.count());
    }
    double sum = 0;
    for (auto d : durations) sum += d;
    return sum / static_cast<double>(runs);
}

} // namespace bench_utils

// ======================================
// Benchmarks for minimal ecs::World class
// ======================================
namespace {

// Benchmark 1: Construct & Destruct single World instance (stack)
void bench_WorldConstructionDestructionStack() {
    // We run inside benchmarkAverage function
    ecs::World w;
    (void)w;
}

// Benchmark 2: Construct & Destruct single World instance (heap)
void bench_WorldConstructionDestructionHeap() {
    std::unique_ptr<ecs::World> w = std::make_unique<ecs::World>();
    // unique_ptr will automatically destruct
}

// Macro-benchmark: Create and Destroy multiple World instances
void bench_MultiWorldCreationDestruction(size_t count) {
    std::vector<std::unique_ptr<ecs::World>> worlds;
    worlds.reserve(count);
    for (size_t i = 0; i < count; ++i) {
        worlds.emplace_back(std::make_unique<ecs::World>());
    }
    worlds.clear();
}

// Since no entity or component management yet, benchmark entity counts with no ops:
// We simulate the "scale" of entity counts by just creating/destroying Worlds
// In real scenario, this would be replaced with createEntity() etc.

} // anonymous namespace

int main() {

    using namespace bench_utils;

    printHeader();

    std::vector<BenchmarkResult> results;

    // --- MICRO BENCHMARKS ---

    // 1) Single World constructor/destructor on stack
    {
        double avgDur = benchmarkAverage(bench_WorldConstructionDestructionStack);
        BenchmarkResult r{
            "World Ctor/Dtor (stack)",
            0,
            avgDur,
            true // No threshold for minimal construct
        };
        printResult(r);
        results.push_back(r);
    }

    // 2) Single World constructor/destructor on heap
    {
        double avgDur = benchmarkAverage(bench_WorldConstructionDestructionHeap);
        BenchmarkResult r{
            "World Ctor/Dtor (heap)",
            0,
            avgDur,
            true
        };
        printResult(r);
        results.push_back(r);
    }

    // --- MACRO BENCHMARKS SIMULATED WITH MULTIPLE OBJECTS ---

    // Since no createEntity yet, we benchmark multiple World objects to simulate "load"
    // Note: This is a placeholder until entity/component methods implemented

    const std::vector<size_t> entityCounts = { 1000, 10'000, 100'000, 1'000'000 };
    const double maxAllowedDurationMs_1M = 20.0; // target for 1M entities
    for (size_t count : entityCounts) {
        // We consider "entityCount" as count to simulate scale even if no entities exist
        // Adjust benchmark to create/destroy 'count' World instances sequentially
        auto func = [count]() {
            bench_MultiWorldCreationDestruction(count);
        };
        // To avoid long test times with 1M Worlds (can be heavy), run only once for 1M
        size_t runs = (count == 1'000'000) ? 1 : 3;
        double avgDur = benchmarkAverage(func, runs);
        bool pass = (count == 1'000'000) ? (avgDur <= maxAllowedDurationMs_1M) : true;
        std::string testName = "Multi World ctor/dtor (" + std::to_string(count) + ")";
        BenchmarkResult r{
            testName,
            count,
            avgDur,
            pass
        };
        printResult(r);
        results.push_back(r);
    }

    // Summary:
    std::cout << "\nSummary:\n";
    bool allPassed = true;
    for (const auto& r : results) {
        if (!r.passed) allPassed = false;
    }
    if (allPassed) {
        std::cout << "All benchmarks PASSED SimplyECS performance targets.\n";
    } else {
        std::cout << "Some benchmarks FAILED SimplyECS performance targets!\n";
    }

    return allPassed ? 0 : 1;
}
```

---

# Açıklamalar ve Notlar

- Mevcut `ecs::World` sınıfı sadece default konstruktor ve destrüktöre sahip olduğu için benchmarklar, nesne oluşturma ve yok etme performansına odaklanmıştır.

- Mikro benchmarklar, tek bir `World` nesnesinin stack ve heap üzerindeki oluşturulma ve yok edilme süresini ölçer.

- Makro benchmarklar, "entity count" parametresi simülasyonu olarak çoklu `World` nesnesi oluşturup yok ederek ölçüm yapar. (Gerçek entity/createEntity yok)

- Gelecekte `createEntity()`, `destroyEntity()` vb. fonksiyonlar eklendiğinde, benchmark kodu bu metodlarla güncellenmelidir.

- 1M entity için 20ms performans hedefi, şu anda 1M World nesnesini oluştur/yok et olarak simüle edilmiştir. Gerçek entity yönetimi eklendiğinde ilgili benchmark güncellenecektir.

- Benchmark sonuçları konsola okunabilir tablolama ile yazdırılır.

- Benchmark fonksiyonları ortalama süreyi almak için 3-5 kez tekrarlanıp ortalama hesaplar.

- Projenin build sistemi ile ilişkilendirilip, benchmark derlenip çalıştırılabilir.

---

Bu benchmark dosyası sadece mevcut MVP aşamasına uygun olup ileride fonksiyonlar eklendikçe detaylandırılmalıdır.