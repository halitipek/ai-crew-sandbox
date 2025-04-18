```cpp
// File: src/benchmark/ClassBenchmark.cpp
//
// Benchmark tests for ecs::World class constructor and destructor.
//
// Even if ecs::World currently has minimal functionality (only default ctor/dtor),
// we'll establish a micro-benchmark template to measure creation & destruction costs
// for large numbers of World instances and single (empty) World instances.
//
// Future ECS features (entity/component creation, access, deletion) will extend this benchmark.
//
// Requirements:
// - Benchmark World creation & destruction for 1K, 10K, 100K, 1M entities scale (entity count simulated).
// - Report durations in ms with clear formatting.
// - Check passed/failed based on simple thresholds where applicable.
// - Output summary to console.
//
// Note:
// Since ecs::World currently doesn't manage entities internally,
// to emulate the benchmark workload we will create 
// multiple World instances sequentially in place of entities,
// simulating construction & destruction overhead.
//
// Performance target for "1M entity <= 20 ms" here will mean:
// Creating and destroying 1M World instances within 20 ms, which is a very loose proxy.
//
// In a real scenario, World would manage entities internally,
// and benchmarks would measure entity ops on a single World instance.
//
// Dependencies: Must include chrono, iostream, vector, and tester-friendly formatting.
//

#include <chrono>
#include <iostream>
#include <vector>
#include <iomanip> // for setw

#include "ecs/World.h"

namespace bench {

// Types
using Clock = std::chrono::high_resolution_clock;
using ms = std::chrono::duration<double, std::milli>;

struct BenchmarkResult {
    std::string testName;
    size_t entityCount;  // simulated entities count (number of World instances)
    double durationMs;
    bool passed;        // based on thresholds
};

class WorldBenchmark {
public:
    // Run default ctor + dtor test by creating and destroying N World instances sequentially.
    // Returns elapsed time in ms.
    static double ctorDtorMultiple(size_t count) {
        auto start = Clock::now();

        {
            std::vector<ecs::World> worlds;
            worlds.reserve(count);
            for (size_t i = 0; i < count; ++i) {
                worlds.emplace_back(); // construct
            }
            // worlds destructor called at scope end
        }

        auto end = Clock::now();
        ms elapsed = end - start;
        return elapsed.count();
    }

    // Run single World ctor/dtor test multiple times and measure average time per instance in ns.
    static double ctorDtorSingleAvgTimeNs(size_t iterations) {
        auto start = Clock::now();

        for (size_t i = 0; i < iterations; ++i) {
            ecs::World w;
            (void)w; // suppress unused warning
        }

        auto end = Clock::now();
        auto totalNs = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        return double(totalNs) / iterations;
    }

    // Print a result line to console in aligned format
    static void printResult(const BenchmarkResult &result) {
        std::cout << std::left << std::setw(30) << result.testName
                  << std::right << std::setw(12) << result.entityCount
                  << std::setw(15) << std::fixed << std::setprecision(3) << result.durationMs << " ms"
                  << std::setw(12) << (result.passed ? "PASSED" : "FAILED")
                  << "\n";
    }

    // Run benchmark battery for different scales and print summary.
    static void runAll() {
        std::cout << "===== SimplyECS World Benchmark =====\n";
        std::cout << "Testing ecs::World default ctor+dtor overhead.\n\n";

        std::cout << std::left << std::setw(30) << "Test"
                  << std::right << std::setw(12) << "Count"
                  << std::setw(15) << "Duration"
                  << std::setw(12) << "Result" << "\n";
        std::cout << std::string(69, '=') << "\n";

        // Test scales simulating entity counts (number of World instances)
        std::vector<size_t> testCounts = { 1000, 10000, 100000, 1000000 };

        // Threshold for 1M count test: total time <= 20ms
        constexpr double thresholdMs_1M = 20.0;

        // Run bulk ctor/dtor tests
        for (size_t count : testCounts) {
            double elapsedMs = ctorDtorMultiple(count);

            // Pass criteria:
            // For 1M entities test, enforce max 20ms
            // For smaller scales, pass unconditionally (no useful threshold yet)
            bool passed = true;
            if (count == 1000000) {
                passed = (elapsedMs <= thresholdMs_1M);
            }

            BenchmarkResult result{
                "World ctor+dtor x count",
                count,
                elapsedMs,
                passed
            };
            printResult(result);
        }

        // Micro-benchmark average time for single World ctor+dtor
        constexpr size_t microIterations = 1000000;
        double avgNs = ctorDtorSingleAvgTimeNs(microIterations);

        std::cout << "\nMicrobenchmark:\n";
        std::cout << "Average World ctor+dtor (single instance): "
                  << std::fixed << std::setprecision(3) << avgNs << " ns\n";

        std::cout << "\nBenchmark complete.\n";
    }
};

} // namespace bench

int main() {
    bench::WorldBenchmark::runAll();
    return 0;
}
```
---

**Açıklamalar:**

- Şu anki kodda `ecs::World` gerçek entity yönetmediği için entity bazlı mikrobenchmark yapılamaz. 
- Testi entity sayısı olarak, o sayıda `ecs::World` nesnesinin oluşturulup yok edilmesiyle proxy olarak ölçüm yapıyoruz.
- Benchmark sonuçları ms cinsinden raporlanıyor, 1M nesne için hedef süre 20 ms olarak kondu.
- Microbenchmark ile tek `ecs::World` nesnesinin oluşturulma-yok edilme süresi nanosaniye cinsinden hesaplanıyor.
- Genel olarak benchmark tasarımı gelecekte ek fonksiyonlar eklenince hızla genişletilebilir.
- Sonuçlar konsola düzgün formatta yazdırılır ve belirlenen eşik değerlere göre "PASSED"/"FAILED" döner.

---

**Kullanım:**

- `SimplyECS` kütüphanesi ile `ecs/World.h` başlık dosyasını içeren derleme ortamında bu benchmark derlenip çalıştırılabilir.
- Konsol çıktısı ölçüm değerlerini ve test sonuçlarını gösterir.
- Daha gelişmiş entity/component işlemleri eklendikçe benchmark da genişletilir.