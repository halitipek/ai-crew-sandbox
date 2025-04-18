```cpp
// File: src/benchmark/ClassBenchmark.cpp

#include <iostream>
#include <chrono>
#include <vector>
#include <string>
#include <iomanip>
#include <stdexcept>
#include <memory>
#include "ecs/World.h"

using namespace ecs;
using namespace std::chrono;

/**
 * @brief Benchmark fixture for ecs::World constructor and destructor performance.
 * 
 * Since currently ecs::World has only default ctor/dtor and no entity storage,
 * this benchmark focuses on measuring the cost of creating and destroying many
 * World instances to simulate workload.
 * 
 * Performance target (for future): Creating and destroying many Worlds should
 * stay efficient without memory leaks or crashes.
 * 
 * Note: Entity-based benchmarks will be added once entity and component APIs exist.
 */

struct BenchmarkResult {
    std::string testName;
    size_t iterations;
    double avgDurationMs;
    bool passed;
};

class WorldBenchmark {
public:
    // Run benchmark of constructing/destroying N World instances in loop
    BenchmarkResult run(size_t iterations) {
        using clock = high_resolution_clock;
        bool exceptionOccurred = false;

        try {
            auto start = clock::now();

            for (size_t i = 0; i < iterations; i++) {
                // Create and immediately destruct World instance (stack scope)
                World w;
                (void)w; // suppress unused warning
            }

            auto end = clock::now();
            duration<double, std::milli> diff = end - start;
            double avgMs = diff.count() / static_cast<double>(iterations);

            // For now, let's require avgMs < 1 ms to consider passing (arbitrary)
            bool pass = (avgMs < 1.0);

            return BenchmarkResult{
                "World ctor/dtor (single objects)",
                iterations,
                avgMs,
                pass
            };
        }
        catch (const std::exception& e) {
            std::cerr << "[Exception] " << e.what() << std::endl;
            exceptionOccurred = true;
        }
        catch (...) {
            std::cerr << "[Unknown exception occurred]" << std::endl;
            exceptionOccurred = true;
        }

        return BenchmarkResult{
            "World ctor/dtor (single objects)",
            iterations,
            0.0,
            !exceptionOccurred
        };
    }

    /**
     * @brief Run "bulk allocation" benchmark:
     * Create N World instances up-front in a container, then destruct all,
     * measuring total time. Useful to check repeated allocations impact.
     */
    BenchmarkResult runBulkAlloc(size_t count) {
        using clock = high_resolution_clock;

        try {
            auto start = clock::now();

            {
                std::vector<World> worlds;
                worlds.reserve(count);
                for (size_t i = 0; i < count; i++)
                    worlds.emplace_back();
                // destructor called on vector clear at scope exit
            }

            auto end = clock::now();
            duration<double, std::milli> diff = end - start;
            double avgMs = diff.count() / static_cast<double>(count);

            // no strict pass criteria but avgMs < 1ms good
            bool pass = (avgMs < 1.0);

            return BenchmarkResult{
                "World batch ctor/dtor (vector storage)",
                count,
                avgMs,
                pass
            };
        }
        catch (const std::exception& e) {
            std::cerr << "[Exception] " << e.what() << std::endl;
        }
        catch (...) {
            std::cerr << "[Unknown exception occurred]" << std::endl;
        }

        return BenchmarkResult{
            "World batch ctor/dtor (vector storage)",
            count,
            0.0,
            false
        };
    }
};

void printBenchmarkResult(const BenchmarkResult& result) {
    std::cout << std::left << std::setw(35) << result.testName 
              << " | Iterations: " << std::setw(10) << result.iterations
              << " | Avg Duration (ms): " << std::fixed << std::setprecision(6) << std::setw(12) << result.avgDurationMs
              << " | Result: " << (result.passed ? "PASS" : "FAIL") << std::endl;
}

int main() {
    // Configured iteration counts for benchmark
    // Since World is very lightweight, we test with 1K, 10K and 100K creations
    // 1M creation causes higher execution times - optional due to test environment.
    constexpr size_t counts[] = { 1000, 10000, 100000 };

    WorldBenchmark bench;

    std::cout << "SimplyECS World Class Benchmark (constructor/destructor performance)" << std::endl;
    std::cout << "--------------------------------------------------------------------" << std::endl;

    for (auto count : counts) {
        auto resSingle = bench.run(count);
        printBenchmarkResult(resSingle);

        auto resBatch = bench.runBulkAlloc(count);
        printBenchmarkResult(resBatch);

        std::cout << std::string(70, '-') << std::endl;
    }

    // Since no entity-level functionality yet, no entity benchmarks possible now.
    std::cout << "NOTE: No entity benchmarks possible at MVP-1 stage." << std::endl;

    return 0;
}
```
---

### Açıklamalar:

- `World` sınıfı çok basit olduğu için benchmarklarda çok sayıda nesne oluşturulup yok edilmeye çalışıldı.
- İstisnaların ortaya çıkmaması ve makul sürelerde (örneğin 1ms altı ortalama) çalışması test edildi.
- Benchmark sonuçları satır satır okunabilir şekilde, PASS/FAIL formatında verilmekte.
- İleride entity & component eklenince, 1K, 10K, 100K, 1M entity benchmarkları eklenebilir.
- Mevcut hedefler (`1M entity <= 20ms`) şimdilik anlamsız çünkü henüz entity yok.
- Benchmark kodu tek dosyada, kolay derlenip çalıştırılabilir.

---

*Not:* Benchmark ileride daha odaklı ölçümler ve daha gelişmiş raporlama için Google Benchmark veya benzeri çerçevelerle değiştirilebilir. Şimdilik bağımsız, minimum kütüphane bağımlı, sade ve anlaşılır yaklaşımla hazırlanmıştır.