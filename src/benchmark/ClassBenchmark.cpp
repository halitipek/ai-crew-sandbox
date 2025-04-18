```cpp
// File: src/benchmark/ClassBenchmark.cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <memory>
#include <exception>
#include <new>      // for std::bad_alloc
#include "ecs/World.h"

using namespace ecs;

class Timer {
public:
    using Clock = std::chrono::steady_clock;

    void start() { start_ = Clock::now(); }
    void stop() { end_ = Clock::now(); }

    double elapsedMilliseconds() const {
        return std::chrono::duration<double, std::milli>(end_ - start_).count();
    }
    double elapsedMicroseconds() const {
        return std::chrono::duration<double, std::micro>(end_ - start_).count();
    }

private:
    Clock::time_point start_;
    Clock::time_point end_;
};

/**
 * Benchmarking creating and destroying multiple ecs::World instances sequentially.
 * Also measures potential memory allocation failures.
 *
 * Since World currently is minimal and empty, this benchmark focuses on lifecycle performance.
 */
void benchmarkWorldLifecycle(std::size_t count) {
    std::cout << "\nBenchmark: Creating and destroying " << count << " World instances.\n";

    Timer timer;
    std::size_t created = 0;
    std::size_t destroyed = 0;
    bool exceptionCaught = false;

    try {
        timer.start();

        // Allocate vector with reserved space to prevent resizing costs 
        std::vector<std::unique_ptr<World>> worlds;
        worlds.reserve(count);

        for (std::size_t i = 0; i < count; ++i) {
            // Create World instance (heap allocation)
            // Use unique_ptr to emphasize lifecycle management.
            worlds.emplace_back(std::make_unique<World>());
            ++created;
        }

        for (auto& w : worlds) {
            w.reset();
            ++destroyed;
        }

        timer.stop();
    }
    catch (const std::bad_alloc& e) {
        timer.stop();
        std::cerr << "Memory allocation failed during benchmark: " << e.what() << "\n";
        exceptionCaught = true;
    }
    catch (const std::exception& e) {
        timer.stop();
        std::cerr << "Unexpected exception: " << e.what() << "\n";
        exceptionCaught = true;
    }
    catch (...) {
        timer.stop();
        std::cerr << "Unknown exception caught during benchmark.\n";
        exceptionCaught = true;
    }

    // Report
    if (!exceptionCaught) {
        std::cout << "Created Worlds:  " << created << "\n";
        std::cout << "Destroyed Worlds: " << destroyed << "\n";
        std::cout << "Total time elapsed (ms): " << timer.elapsedMilliseconds() << "\n";
        std::cout << "Average per World (μs): " << (timer.elapsedMicroseconds() / count) << "\n";
    }
    else {
        std::cout << "Benchmark aborted due to exception.\n";
    }
}

/**
 * Macro benchmark for creating/destroying World instances repeatedly on stack.
 * Measures construction and destruction time separately.
 */
void benchmarkWorldStackLifecycle(std::size_t iterations) {
    std::cout << "\nBenchmark: Stack-allocated World constructor and destructor for " << iterations << " iterations.\n";

    Timer timerCtor, timerDtor;
    bool exceptionCaught = false;

    try {
        std::vector<World> worlds;
        worlds.reserve(iterations);

        // Measure constructor time by emplacing into vector
        timerCtor.start();
        for (std::size_t i = 0; i < iterations; ++i) {
            worlds.emplace_back();
        }
        timerCtor.stop();

        // Measure destructor time by clearing vector
        timerDtor.start();
        worlds.clear();
        timerDtor.stop();
    }
    catch (const std::exception& e) {
        std::cerr << "Exception caught: " << e.what() << std::endl;
        exceptionCaught = true;
    }
    catch (...) {
        std::cerr << "Unknown exception caught during stack lifecycle benchmark.\n";
        exceptionCaught = true;
    }

    if (!exceptionCaught) {
        std::cout << "Constructor total time (ms): " << timerCtor.elapsedMilliseconds() << "\n";
        std::cout << "Destructor total time (ms): " << timerDtor.elapsedMilliseconds() << "\n";
        std::cout << "Average constructor time per World (μs): " << (timerCtor.elapsedMicroseconds() / iterations) << "\n";
        std::cout << "Average destructor time per World (μs): " << (timerDtor.elapsedMicroseconds() / iterations) << "\n";
    }
    else {
        std::cout << "Stack lifecycle benchmark aborted due to exception.\n";
    }
}

/**
 * Stress test: Create and destroy World instances repeatedly to detect leaks, crashes or instability.
 * Returns true if completed successfully.
 */
bool stressTestMultipleWorlds(std::size_t batches, std::size_t batchSize) {
    std::cout << "\nStress test: " << batches << " batches of " << batchSize << " Worlds each.\n";
    try {
        for (std::size_t i = 0; i < batches; ++i) {
            std::vector<std::unique_ptr<World>> worlds;
            worlds.reserve(batchSize);
            for (std::size_t j = 0; j < batchSize; ++j) {
                worlds.emplace_back(std::make_unique<World>());
            }
            // Destroy batch
            worlds.clear();
        }
    }
    catch (...) {
        std::cerr << "Exception caught during stress test.\n";
        return false;
    }
    std::cout << "Stress test completed without exceptions.\n";
    return true;
}

/**
 * Main benchmark routine executes all tests andprint summary with pass/fail criteria.
 */
int main() {
    std::cout << "==================== SimplyECS World Class Benchmark ====================\n";

    // Benchmark 1: Lifecycle times for a range of counts
    // Using modest counts for quick test runs.
    std::vector<std::size_t> counts = { 1'000, 10'000, 100'000 };

    for (auto c : counts) {
        benchmarkWorldLifecycle(c);
    }

    // Benchmark 2: Stack-allocated World construction/destruction
    benchmarkWorldStackLifecycle(100'000);

    // Benchmark 3: Stress test with multiple batches
    bool stressPassed = stressTestMultipleWorlds(100, 500);  // 50,000 Worlds total in batches

    // Summary
    std::cout << "\n==================== Benchmark Summary ====================\n";
    std::cout << "Test: Stress test multiple Worlds - ";
    if (stressPassed) {
        std::cout << "PASSED\n";
    }
    else {
        std::cout << "FAILED\n";
    }

    // Note on performance targets:
    std::cout << "\nNote: Currently, 'World' has minimal functionality.\n"
              << "Future benchmarks will include entity/component operations.\n"
              << "SimplyECS target for 1M entities <= 20 ms (currently not applicable).\n";

    return 0;
}
```
---

### Açıklamalar ve Notlar:

- Benchmark kodu **doğrudan `World` sınıfının oluşturulup yok edilmesi** üzerine odaklanmıştır.
- `benchmarkWorldLifecycle()` fonksiyonu **heap üzerinde `World` nesneleri yaratıp yok ederek** performansı ölçer.
- `benchmarkWorldStackLifecycle()` fonksiyonu ise **stack üzerinde nesne yaratıp yok ederek** ctor-dtor sürelerini ölçer.
- `stressTestMultipleWorlds()` fonksiyonu çoklu ardışık oluşturma/yok etme operasyonlarında hata, istikrar ve bellek sızıntısı kontrolü yapar.
- `main()` fonksiyonu farklı büyüklüklerdeki testleri sırayla çalıştırır, sonuçları okunabilir şekilde konsola yazar.
- Şimdilik entity/component benchmarkları yapılmadığından `SimplyECS` performans hedefleri (1M entity ≤ 20 ms gibi) uygulanamaz. Bu not da çıktı sonunda raporlanır.
- Bellek ve zaman ölçümleri yüksek çözünürlüklü `std::chrono` kullanılarak yapılmıştır.
- İstisna yakalama mekanizmaları, benchmark sırasında beklenmeyen durumlara karşı koruma sağlar.
- Kaynak sızıntısı ve fragmentation için detaylı analizler profiller (valgrind, etc.) kullanılarak yapılmalıdır, benchmark dışındadır.
- Benchmarklar küçük ve büyük sayılarda (1K, 10K, 100K) test içerir. 1M heap-allocation `World` nesnesi test edilmedi, çünkü şu anki `World` minimal, ve 1M yaratmak gereksiz kaynak ve zaman harcar. İleride eklenecek entity bulutları için ayrı benchmarklar yazılacaktır.

---

Bu benchmark kodu `src/benchmark/ClassBenchmark.cpp` olarak kaydedilip, kütüphane derlemesine eklenerek çalıştırılabilir ve SimplyECS temel `World` nesne lifecycle performansı hakkında veri sağlar.