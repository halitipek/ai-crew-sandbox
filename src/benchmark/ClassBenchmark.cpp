```cpp
// File: src/benchmark/ClassBenchmark.cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <string>
#include <iomanip>  // setw, setprecision

#include "ecs/World.h"

using namespace ecs;
using Clock = std::chrono::high_resolution_clock;
using namespace std::chrono_literals;

/**
 * @brief Utility RAII timer for benchmarking scopes.
 */
class ScopedTimer {
public:
    ScopedTimer(std::string_view message)
        : m_message(message), m_start(Clock::now()) {}

    ~ScopedTimer() {
        auto end = Clock::now();
        auto durationMs = std::chrono::duration_cast<std::chrono::microseconds>(end - m_start).count() / 1000.0;
        std::cout << m_message << ": " << std::fixed << std::setprecision(3) << durationMs << " ms\n";
        m_lastDurationMs = durationMs;
    }

    double durationMs() const { return m_lastDurationMs; }

private:
    std::string m_message;
    Clock::time_point m_start;
    double m_lastDurationMs = 0.0;
};

/**
 * @brief Run microbenchmark: create/destroy single World instance multiple times.
 * Microbenchmark focuses on World ctor/dtor overhead.
 *
 * @param iterations How many times the World instance is created/destroyed.
 * @return double average duration (ms)
 */
double microBenchmark_WorldCtorDtor(std::size_t iterations) {
    auto start = Clock::now();
    for (std::size_t i = 0; i < iterations; ++i) {
        World w;
        (void)w; // suppress unused warning
    }
    auto end = Clock::now();
    double durationMs = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count() / 1000.0;
    return durationMs / iterations;
}

/**
 * @brief Macro benchmark scenario:
 * Create a large vector (size N) of Worlds on heap and destroy them,
 * measuring creation time and destruction time separately.
 *
 * Since current World has no meaningful data/methods,
 * this simulates overhead of default ctor and dtor for many instances.
 *
 * @param entityCounts vector of entity counts to simulate load.
 */
void macroBenchmark_World_CreateDestroy(const std::vector<std::size_t>& entityCounts) {
    std::cout << "\n--- Macro Benchmark: World create/destroy for multiple sizes ---\n";

    for (auto N : entityCounts) {
        std::cout << "Testing with " << N << " World instances.\n";

        double creationTimeMs = 0.0;
        double destructionTimeMs = 0.0;

        // Measure creation time
        {
            auto start = Clock::now();
            std::vector<World*> worlds;
            worlds.reserve(N);
            for (std::size_t i = 0; i < N; ++i)
                worlds.push_back(new World());
            auto end = Clock::now();
            creationTimeMs = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count() / 1000.0;

            // Measure destruction time
            start = Clock::now();
            for (auto ptr : worlds) delete ptr;
            end = Clock::now();
            destructionTimeMs = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count() / 1000.0;
        }

        double totalMs = creationTimeMs + destructionTimeMs;

        // Expected: For 1M instances <= 20ms total.
        bool pass = (N == 1000000) ? (totalMs <= 20.0) : true;

        std::cout << std::fixed << std::setprecision(3)
                  << "Create time: " << creationTimeMs << " ms, "
                  << "Destroy time: " << destructionTimeMs << " ms, "
                  << "Total: " << totalMs << " ms - "
                  << (pass ? "PASS" : "FAIL") << "\n\n";
    }
}

/**
 * @brief Run benchmark suite.
 * Prints results to console with pass/fail according to performance goals.
 */
void runBenchmarks() {
    std::cout << "SimplyECS World class benchmark suite\n";
    std::cout << "-------------------------------------\n";

    // Microbenchmark: ctor/dtor call overhead average measurement
    constexpr std::size_t microIterations = 1000000;
    {
        std::cout << "\nMicrobenchmark: Average World ctor+dtor time (" << microIterations << " iterations)\n";
        double avgTimeMs = microBenchmark_WorldCtorDtor(microIterations);
        std::cout << "Average ctor+dtor: " << std::fixed << std::setprecision(6) << avgTimeMs << " ms\n";
        // No strict pass/fail here, just measurement.
    }

    // Macrobenchmarks - simulating entity counts by creating multiple World instances.
    // NOTE:
    // Current World does NOT truly represent entities/components, but use this to measure ctor/dtor scaling.
    std::vector<std::size_t> entityCounts = { 1000, 10000, 100000, 1000000 };
    macroBenchmark_World_CreateDestroy(entityCounts);

    std::cout << "Benchmark suite complete.\n\n";
}

int main() {
    try {
        runBenchmarks();
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Exception caught during benchmarks: " << ex.what() << '\n';
        return 1;
    } catch (...) {
        std::cerr << "Unknown exception caught during benchmarks\n";
        return 2;
    }
}
```

---

# Açıklamalar ve Detaylar

- **Mikro benchmark:** Tek tek `World` nesnesinin oluşturulma ve yok edilme süresi, 1M kez tekrar edilerek ortalaması alınır.
- **Makro benchmark:** Farklı büyüklüklerde (1K, 10K, 100K, 1M) `World` örnekleri heap'te yaratılır ve yok edilir. Bu sayede `ctor` ve `dtor` üzerindeki toplam yük ölçülür.
- **Performans hedefleri:** 1M entity için toplam ctor+dtor zamanı <= 20 ms olmalıdır (şimdilik `World` nesnesi, gerçek entity yönetimini temsil etmediği için referans olarak aynı limit kullanılır).
- **Sonuçlar:** Konsola net, okunabilir şekilde yazdırılır; testin geçtiği veya kaldığı durumda bilgi verilir.
- **Hazırlık:** Kütüphanenin gelecekte eklenecek fonksiyonları dolayısıyla benchmark altyapısı genişletilebilir olacak.
- **Bellek yönetimi:** `new` ve `delete` kullanılarak testi gerçekçi hale getirdim; benchmark bitince tüm kaynaklar temizlenmiş olur (örnek).  

---

# Not

Şu an `ecs::World` sınıfı minimal olduğu için entity ve component bazlı gerçek benchmarklar mümkün değil. En uygun şimdilik ctor-dtor ölçek testi sağlanabilir. İlerleyen versiyonlarda `createEntity()`, `addComponent<T>()` vb. özellikler eklendiğinde ilgili benchmarklar genişletilmelidir.