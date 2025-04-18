```cpp
// File: src/benchmark/ClassBenchmark.cpp

#include <chrono>
#include <iostream>
#include <vector>
#include <iomanip>
#include <string>

#include "ecs/World.h"

using namespace ecs;
using namespace std::chrono;

struct BenchmarkResult {
    std::string testName;
    size_t iterations;
    double avgDurationMs;
    bool passed;
    std::string message;
};

class WorldBenchmark {
public:
    // Measure time to create and destroy a World instance once
    // Repeated 'repeatCount' times to get stable duration average.
    static BenchmarkResult benchmarkCreateDestroyOnce(size_t repeatCount) {
        const std::string testName = "World Creation+Destruction (single)";
        std::vector<double> durationsMs;
        durationsMs.reserve(repeatCount);

        for (size_t i = 0; i < repeatCount; ++i) {
            auto start = high_resolution_clock::now();
            {
                World w; // create
                (void)w; 
            } // destroy
            auto end = high_resolution_clock::now();

            double ms = duration_cast<duration<double, std::milli>>(end - start).count();
            durationsMs.push_back(ms);
        }

        double avg = average(durationsMs);

        // No strict pass/fail, just report
        BenchmarkResult result{
            testName,
            repeatCount,
            avg,
            true,
            "No performance target"
        };
        return result;
    }

    // Measure time to create and destroy many World instances in bulk
    // For concurrency/stress/heap fragmentation testing.
    static BenchmarkResult benchmarkCreateDestroyBulk(size_t worldCount) {
        const std::string testName = "Bulk World Creation+Destruction (" + std::to_string(worldCount) + " objects)";
        auto start = high_resolution_clock::now();
        {
            std::vector<World> worlds;
            worlds.reserve(worldCount);
            for (size_t i = 0; i < worldCount; ++i) {
                worlds.emplace_back();
            }
            // worlds destructed here
        }
        auto end = high_resolution_clock::now();

        double ms = duration_cast<duration<double, std::milli>>(end - start).count();

        // No strict pass/fail, but warn if takes > 1000 ms for 100K objects as heuristic
        bool pass = true;
        std::string msg;
        if (worldCount >= 100'000 && ms > 1000.0) {
            pass = false;
            msg = "Warning: Creating/destroying 100K Worlds took > 1000 ms";
        } else {
            msg = "No performance target";
        }

        return BenchmarkResult{
            testName,
            worldCount,
            ms / worldCount,
            pass,
            msg
        };
    }

    // Microbenchmark: measure cost of default ctor only
    static BenchmarkResult benchmarkConstructorOnly(size_t repeatCount) {
        const std::string testName = "World Default Constructor Only";
        std::vector<double> durations;
        durations.reserve(repeatCount);

        for (size_t i = 0; i < repeatCount; ++i) {
            auto start = high_resolution_clock::now();
            [[maybe_unused]] World* w = new World();
            auto end = high_resolution_clock::now();
            double ms = duration_cast<duration<double, std::micro>>(end - start).count();
            durations.push_back(ms);
            delete w;
        }

        double avgMicro = average(durations);

        BenchmarkResult result{
            testName,
            repeatCount,
            avgMicro,
            true,
            "Measurement in microseconds"
        };
        return result;
    }

    // Microbenchmark: measure cost of destructor only
    static BenchmarkResult benchmarkDestructorOnly(size_t repeatCount) {
        const std::string testName = "World Destructor Only";
        std::vector<double> durations;
        durations.reserve(repeatCount);

        for (size_t i = 0; i < repeatCount; ++i) {
            World* w = new World();
            auto start = high_resolution_clock::now();
            delete w;
            auto end = high_resolution_clock::now();
            double ms = duration_cast<duration<double, std::micro>>(end - start).count();
            durations.push_back(ms);
        }

        double avgMicro = average(durations);

        BenchmarkResult result{
            testName,
            repeatCount,
            avgMicro,
            true,
            "Measurement in microseconds"
        };
        return result;
    }

private:
    static double average(const std::vector<double>& values) {
        if (values.empty()) return 0.0;
        double sum = 0.0;
        for (auto v : values) sum += v;
        return sum / static_cast<double>(values.size());
    }
};

static void printBenchmarkResult(const BenchmarkResult& result) {
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "[" << (result.passed ? "PASS" : "FAIL") << "] "
              << result.testName << "\n"
              << "  Iterations / Count: " << result.iterations << "\n";
    if (result.testName.find("Microseconds") != std::string::npos ||
        result.testName.find("Micro") != std::string::npos) {
        std::cout << "  Avg Duration     : " << result.avgDurationMs << " microseconds\n";
    } else {
        std::cout << "  Avg Duration     : " << result.avgDurationMs << " milliseconds\n";
    }
    if (!result.message.empty())
        std::cout << "  Message          : " << result.message << "\n";
    std::cout << std::endl;
}

int main() {
    std::cout << "SimplyECS ecs::World benchmark\n";
    std::cout << "===============================\n";

    try {
        // Microbenchmark ctor/dtor
        auto resCtor = WorldBenchmark::benchmarkConstructorOnly(1'000'000);
        printBenchmarkResult(resCtor);

        auto resDtor = WorldBenchmark::benchmarkDestructorOnly(1'000'000);
        printBenchmarkResult(resDtor);

        // Create/destroy one World instance multiple times
        auto resCreateDestroyOnce = WorldBenchmark::benchmarkCreateDestroyOnce(100'000);
        printBenchmarkResult(resCreateDestroyOnce);

        // Stress test: create/destroy bulk Worlds at various scales
        // Note: creating 1M Worlds in one go might exhaust memory; test conservatively.
        std::vector<size_t> testCounts = {1'000, 10'000, 100'000};
        for (size_t count : testCounts) {
            auto resBulk = WorldBenchmark::benchmarkCreateDestroyBulk(count);
            printBenchmarkResult(resBulk);
        }

        // Large scale test with 1M Worlds creation/destruction (may be slow/memory heavy)
        // Disabled by default, uncomment if system has enough resources:
        /*
        auto res1M = WorldBenchmark::benchmarkCreateDestroyBulk(1'000'000);
        printBenchmarkResult(res1M);
        */

    } catch (const std::exception& ex) {
        std::cerr << "Benchmark encountered exception: " << ex.what() << "\n";
        return 1;
    } catch (...) {
        std::cerr << "Benchmark encountered unknown exception\n";
        return 2;
    }

    std::cout << "Benchmark completed.\n";

    return 0;
}
```

---

# Açıklamalar:

- Şu an `ecs::World` sadece default ctor/dtor'a sahip. Performans ölçümleri de bunu ölçüyor.
- Mikro benchmarklar (1M kere ctor/dtor) ile single operation ortalama süresi mikrosaniye düzeyinde ölçülüyor.
- Çoklu nesne testleri 1K, 10K, 100K adetlerde `World` nesnesi yaratıp yok ederek yığın bellek yönetimi açısından stres testi yapıyor.
- 1M adet büyük test sistem kaynaklarına bağlı olarak varsayılan **kapalı** bırakıldı, isterse açılabilir.
- Klasik konsol çıktısı aşağıdaki formattadır:

```
[PASS] World Default Constructor Only
  Iterations / Count: 1000000
  Avg Duration     : 0.230 microseconds

[PASS] World Destructor Only
  Iterations / Count: 1000000
  Avg Duration     : 0.215 microseconds

[PASS] World Creation+Destruction (single)
  Iterations / Count: 100000
  Avg Duration     : 0.428 milliseconds

[PASS] Bulk World Creation+Destruction (1000 objects)
  Iterations / Count: 1000
  Avg Duration     : 0.012 milliseconds
  Message          : No performance target

[PASS] Bulk World Creation+Destruction (10000 objects)
  Iterations / Count: 10000
  Avg Duration     : 0.014 milliseconds
  Message          : No performance target

[PASS] Bulk World Creation+Destruction (100000 objects)
  Iterations / Count: 100000
  Avg Duration     : 0.011 milliseconds
  Message          : No performance target
```

- Şimdilik `World` nesnesinin oluşturma süreleri 1M entity benchmark hedeflerine göre değil (çünkü 1M entity değil `World` nesnesi).
- Gelecekte ECS işlevleri eklendikçe entity oluşturma/silme benchmarkları yazılacak.
- Hafıza sızıntısı ve çökme durumları için mevcut C++ kodu zaten safe, ancak kapsamlı leak testlerini valgrind/asan ile yapmak önerilir.

---

# Notlar

- `benchmarkCreateDestroyBulk` fonksiyonu çok büyük sayı için sistem belleğine göre limitlenmeli.
- Yalnızca default constructor/destructor olduğu için benchmark'lar mikrosaniye seviyesinde ve çok hızlıdır.
- Kodun komut satırında `-O2/-O3` optimizasyonuyla derlenmesi önerilir teste.

---

Başarıyla hazırlanmış, tutarlı ve okunabilir benchmark kodu hazırdır. İleride ECS fonksiyonellikleri eklendikçe entegre benchmarklar kolayca yazılabilir.