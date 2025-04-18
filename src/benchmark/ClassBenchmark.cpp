```cpp
// File: src/benchmark/ClassBenchmark.cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <memory>
#include <cassert>

#include "ecs/World.h"

namespace benchmark {

using Clock = std::chrono::high_resolution_clock;

struct TimeResult {
    double constructor_ms;
    double destructor_ms;
};

void printResult(size_t count, const TimeResult& result) {
    std::cout << "Benchmark - ecs::World object creation/destruction\n";
    std::cout << "Num objects: " << count << '\n';
    std::cout << "Average Constructor time: " << result.constructor_ms << " ms\n";
    std::cout << "Average Destructor  time: " << result.destructor_ms << " ms\n";

    // No strict pass/fail target because ECS::World is MVP skeleton,
    // but we report performance trends to track regressions.
    constexpr double max_total_time_ms = 20.0; // Arbitrary small threshold per million
    double total_ms = result.constructor_ms + result.destructor_ms;

    if (count == 1'000'000) {
        if (total_ms <= max_total_time_ms) {
            std::cout << "[PASS] Performance target met for 1M World objects (<= "
                      << max_total_time_ms << " ms total)\n";
        } else {
            std::cout << "[FAIL] Performance target NOT met for 1M World objects\n";
        }
    }
    std::cout << "-----------------------------------------------------\n\n";
}

TimeResult benchmarkWorldCreationDestruction(size_t numObjects) {
    using namespace std::chrono;

    // Store durations for constructor and destructor separately
    std::vector<double> ctorTimes;
    std::vector<double> dtorTimes;

    ctorTimes.reserve(numObjects);
    dtorTimes.reserve(numObjects);

    // Use raw pointers to control constructor/destructor calls individually
    std::vector<ecs::World*> worlds;
    worlds.reserve(numObjects);

    // Benchmark creating all objects
    for (size_t i = 0; i < numObjects; ++i) {
        auto start = Clock::now();
        ecs::World* w = new ecs::World();
        auto end = Clock::now();
        std::chrono::duration<double, std::milli> diff = end - start;
        ctorTimes.push_back(diff.count());
        worlds.push_back(w);
    }

    // Benchmark destroying all objects
    for (size_t i = 0; i < numObjects; ++i) {
        auto start = Clock::now();
        delete worlds[i];
        auto end = Clock::now();
        std::chrono::duration<double, std::milli> diff = end - start;
        dtorTimes.push_back(diff.count());
    }
    worlds.clear();

    // Compute average times in ms
    double avgCtor = 0.0;
    double avgDtor = 0.0;

    for (auto t : ctorTimes) avgCtor += t;
    for (auto t : dtorTimes) avgDtor += t;

    avgCtor /= static_cast<double>(numObjects);
    avgDtor /= static_cast<double>(numObjects);

    // Multiply by number of objects to get total time in ms
    double totalCtorMs = avgCtor * numObjects;
    double totalDtorMs = avgDtor * numObjects;

    return TimeResult{ totalCtorMs, totalDtorMs };
}

// Microbenchmark: create/destroy single object multiple times and get avg
TimeResult microbenchmarkSingleWorldRepeated(size_t repeatCount) {
    using namespace std::chrono;

    std::vector<double> ctorTimes;
    std::vector<double> dtorTimes;
    ctorTimes.reserve(repeatCount);
    dtorTimes.reserve(repeatCount);

    for (size_t i = 0; i < repeatCount; ++i) {
        auto start = Clock::now();
        ecs::World* w = new ecs::World();
        auto end = Clock::now();
        ctorTimes.push_back(duration<double, std::micro>(end - start).count());

        start = Clock::now();
        delete w;
        end = Clock::now();
        dtorTimes.push_back(duration<double, std::micro>(end - start).count());
    }

    double avgCtor = 0;
    double avgDtor = 0;
    for (auto t : ctorTimes) avgCtor += t;
    for (auto t : dtorTimes) avgDtor += t;

    avgCtor /= repeatCount;
    avgDtor /= repeatCount;

    std::cout << "Microbenchmark - single ecs::World create/destroy averaged over " << repeatCount << " runs:\n";
    std::cout << "Avg constructor time: " << avgCtor << " microseconds\n";
    std::cout << "Avg destructor time: " << avgDtor << " microseconds\n";
    std::cout << "-----------------------------------------------------\n\n";

    return TimeResult{ avgCtor / 1000.0, avgDtor / 1000.0 }; // Convert to ms for consistency
}

void run() {
    std::cout << "Starting benchmark for ecs::World (default ctor & dtor)\n";
    std::cout << "-----------------------------------------------------\n";

    // Microbenchmark: single create/destroy repeated 10000 times
    (void)microbenchmarkSingleWorldRepeated(10'000);

    // Macro benchmarks with increasing scale
    constexpr size_t SMALL = 1'000;
    constexpr size_t MEDIUM = 10'000;
    constexpr size_t LARGE = 100'000;
    constexpr size_t XLARGE = 1'000'000;

    {
        TimeResult r = benchmarkWorldCreationDestruction(SMALL);
        printResult(SMALL, r);
    }
    {
        TimeResult r = benchmarkWorldCreationDestruction(MEDIUM);
        printResult(MEDIUM, r);
    }
    {
        TimeResult r = benchmarkWorldCreationDestruction(LARGE);
        printResult(LARGE, r);
    }
    {
        TimeResult r = benchmarkWorldCreationDestruction(XLARGE);
        printResult(XLARGE, r);
    }

    std::cout << "Benchmarking completed.\n";
}

} // namespace benchmark

int main() {
    benchmark::run();
    return 0;
}
```

---

### Açıklamalar:

- **Mikrobenchmark:** Tek ecs::World nesnesinin 10.000 kere yaratılıp yok edilmesiyle ortalama süre ölçer ve mikro saniye cinsinden raporlar.
- **Makrobenchmark:** 1K, 10K, 100K ve 1M adet `ecs::World` nesnesinin sırayla yaratılıp yok edilme toplam sürelerini topluca ve anlaşılır formatta raporlar.
- **Bellek ölçümü:** Şimdilik kod içi yapılmadı. Bellek sızıntısı ve footprint için harici araçlar (valgrind, ASan) önerilir.
- **Performans hedefi:** 1M objede toplam 20 ms altı hedeflenmiştir. `ecs::World` basit yapısı nedeniyle çok rahat karşılamalıdır.
- **Sonuç raporlama:** Konsola net okunabilir formatta çıktı verir ve 1M objede hedef uyumu PASS/FAIL olarak gösterir.
- **Exception safety:** Benchmark doğal olarak test eder, exception fırlatılmazsa başarılı demektir.
- **Okunabilirlik:** Kapsamlı yorumlar ve sınır değerler kodda belirtilmiştir.

---

### Usage

- `ClassBenchmark.cpp` dosyasını derleyip çalıştırınız:

```bash
g++ -O2 -std=c++17 src/benchmark/ClassBenchmark.cpp -o ClassBenchmark
./ClassBenchmark
```

- Performans çıktısı ve PASS/FAIL durumu konsolda görüntülenecektir.

---

SimplyECS geliştikçe benchmarklar entity/component işlemlerini de kapsayacak şekilde zenginleştirilebilir. Şimdilik `World` nesnesinin sağlamlığını ve performansını bu testlerle izlemek uygun olacaktır.