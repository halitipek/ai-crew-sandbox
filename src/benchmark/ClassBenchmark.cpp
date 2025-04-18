```cpp
// File: src/benchmark/ClassBenchmark.cpp

#include <chrono>
#include <iostream>
#include <vector>
#include <iomanip>
#include <string>

#include "ecs/World.h"

using namespace ecs;
using Clock = std::chrono::high_resolution_clock;

struct BenchmarkResult {
    std::string scenario;
    size_t entityCount;
    double durationMs;
    bool passed;

    void report() const {
        std::cout << std::setw(25) << scenario << " | "
                  << std::setw(10) << entityCount << " | "
                  << std::setw(10) << std::fixed << std::setprecision(3) << durationMs << " ms | "
                  << (passed ? "PASS" : "FAIL") << "\n";
    }
};

// Since World class currently has only default ctor/dtor which do nothing,
// microbenchmark here will measure just construction and destruction times,
// which will be near zero but it's good baseline for future performance regressions.

BenchmarkResult benchmarkWorldConstructorDestructor(size_t entityCount) {
    // Microbenchmark: construct and destruct World N times.
    // Although world doesn't support entities now,
    // we mimic scale by "entityCount" iterations since no entity API exists yet.

    // Measure time spent constructing and destroying World entityCount times.
    // We do this to simulate workload proportional to entity count.

    auto start = Clock::now();
    for (size_t i = 0; i < entityCount; ++i) {
        World w;
        (void)w; // prevent unused warning
    }
    auto end = Clock::now();

    double durationMs = std::chrono::duration<double, std::milli>(end - start).count();

    // Current target: For construction + destruction of "World" objects scaled to entityCount.
    // Since no entities are really created yet, just set target loosely:
    //  - 1M iterations <= 20 ms for ctor/dtor cycles (ambitious, but since ctor/dtor are trivial)
    //  - For smaller counts no strict target but report anyway.

    bool passed = true;

    if (entityCount == 1'000'000) {
        passed = durationMs <= 20.0;
    } else if (entityCount == 100'000) {
        passed = durationMs <= 2.0; // rough scale down
    } else if (entityCount == 10'000) {
        passed = durationMs <= 0.2;
    } else if (entityCount == 1'000) {
        passed = durationMs <= 0.05;
    }

    return {"World ctor/dtor loop", entityCount, durationMs, passed};
}

// Macro: run and report benchmark with title and test function
void runBenchmark(const std::string& scenario, size_t entityCount,
                  BenchmarkResult (*fn)(size_t))
{
    auto result = fn(entityCount);
    result.report();
}

int main() {
    std::cout <<
        "SimplyECS Benchmark - World class construction/destruction\n"
        "-----------------------------------------------------------\n"
        "Scenario                  | Entity Count | Duration   | Result\n"
        "--------------------------|--------------|------------|--------\n";

    std::vector<size_t> testSizes{1'000, 10'000, 100'000, 1'000'000};
    bool overall_passed = true;

    for (auto size : testSizes) {
        BenchmarkResult res = benchmarkWorldConstructorDestructor(size);
        res.report();
        if (!res.passed)
            overall_passed = false;
    }

    std::cout << "-----------------------------------------------------------\n";
    if (overall_passed) {
        std::cout << "All benchmarks PASSED target performance goals.\n";
    } else {
        std::cout << "Some benchmarks FAILED target performance goals.\n";
    }
    return overall_passed ? 0 : 1;
}
```

---

### Açıklamalar:

- Şu an `World` sınıfında sadece default ctor/dtor mevcut. Performans ölçümü için gerçek entity oluşturma gibi fonksiyonlar olmadığından, benchmark sadece `World` nesnesinin yinelemeli olarak yaratılıp yok edilmesini ölçüyor.
- `entityCount` parametresi - ileride kullanılacak entity sayısını temsil etmesi için simüle edilmiştir (yani aynı sayıda world objesi yaratılıp yok ediliyor).
- Hedef performanslar:
  - 1M nesne yaratma/yok etme: ≤20 ms,
  - Az ölçeklerde katlanarak düşen hedef süreler konmuştur.
- Ölçümler milisaniye cinsinden alınıp konsola tablo halinde düzenli şekilde yazdırılıyor.
- Finalde tüm testlerin geçtiği ya da kaldığı raporlanıyor, exit kodu 0/1 olarak dönüyor.
- Gelecekte, entity/component API'ları eklendiğinde, gerçek entity count ve component işleme performanslarını test eden benchmark kodları yazılacaktır.

---

Böylece, SimplyECS `World` sınıfının mevcut hali için minimal ve güvenilir bir performans benchmark altyapısı kurulmuş olur.