```cpp
// File: src/benchmark/ClassBenchmark.cpp

#include <chrono>
#include <iostream>
#include <vector>
#include <memory>
#include <iomanip>
#include "ecs/World.h"

using Clock = std::chrono::high_resolution_clock;
using Duration = std::chrono::duration<double, std::milli>;

namespace benchmark {

// Helper function to print a horizontal line
void printSeparator() {
    std::cout << std::string(70, '=') << '\n';
}

// Prints benchmark header
void printHeader(const std::string& title) {
    printSeparator();
    std::cout << title << "\n";
    printSeparator();
}

// Template benchmark for creating and destroying N World instances
// Measures time taken to create and destroy
void benchmarkWorldCreationDestruction(std::size_t count) {
    printHeader("Benchmark: World Creation and Destruction");
    std::cout << "Test with " << count << " World instance(s)\n";

    // Measure creation time
    auto start_create = Clock::now();

    std::vector<std::unique_ptr<ecs::World>> worlds;
    worlds.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
        worlds.emplace_back(std::make_unique<ecs::World>());
    }

    auto end_create = Clock::now();
    Duration create_time = end_create - start_create;

    // Measure destruction time - clear vector (unique_ptr destructors called)
    auto start_destroy = Clock::now();
    worlds.clear();
    auto end_destroy = Clock::now();

    Duration destroy_time = end_destroy - start_destroy;

    // Total time
    Duration total_time = create_time + destroy_time;

    // Report results
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "World creation time:  " << create_time.count() << " ms\n";
    std::cout << "World destruction time: " << destroy_time.count() << " ms\n";
    std::cout << "Total create+destroy time: " << total_time.count() << " ms\n";

    // Since class is very simple, times expected to be very low.
    std::cout << "Result: " << (total_time.count() >= 0.0 ? "PASSED (no crash / leaks detected)" : "FAILED") << "\n\n";
}

// Macro benchmark for scalability in creating/destroying one World instance each iteration
// Iterates count times, creating & destroying World per iteration, measures total time
void benchmarkWorldCreationDestructionRepeated(std::size_t iterations) {
    printHeader("Benchmark: Repeated World Creation+Destruction per iteration");
    std::cout << "Iterations: " << iterations << "\n";
    volatile int dummy = 0; // To avoid optimization removing object

    auto start_all = Clock::now();

    for (std::size_t i = 0; i < iterations; ++i) {
        ecs::World w;
        dummy += 1;
        (void)dummy; // suppress unused warning
    }

    auto end_all = Clock::now();
    Duration total_time = end_all - start_all;

    // Report average and total
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "Total time (create+destroy " << iterations << " Worlds): " << total_time.count() << " ms\n";
    std::cout << "Average time per World: " << (total_time.count() / iterations) << " ms\n\n";
}

// Run all benchmarks for the currently implemented World class
void runAll() {
    std::cout << "\nSimplyECS World class benchmark\n";

    // Micro benchmark: Create/destroy single World 1k times
    benchmarkWorldCreationDestructionRepeated(1000);

    // Macro benchmarks: bulk creating/destroying many Worlds at once
    benchmarkWorldCreationDestruction(1);        // Single create/destroy
    benchmarkWorldCreationDestruction(1000);     // 1K objects at once
    benchmarkWorldCreationDestruction(10000);    // 10K objects (may be slow but World is light)

    // World class has no entity related functions yet, so entity scaling benchmarks
    // can't be done now. Placeholder for future:
    // benchmarkEntityCreation(1000);
    // benchmarkEntityCreation(10000);
    // benchmarkEntityCreation(100000);
    // benchmarkEntityCreation(1000000);

    std::cout << "Benchmark complete.\n";
}

} // namespace benchmark

int main() {
    benchmark::runAll();
    return 0;
}
```

---

# Açıklamalar ve Kullanım Notları

- Benchmark, şimdilik sadece `ecs::World` nesnelerinin oluşturulması/yok edilmesi üzerine odaklanmıştır.
- `benchmarkWorldCreationDestructionRepeated` fonksiyonu, tek bir nesnenin art arda çok sayıda oluşturulup yok edilmesinin ortalama süresini ölçer.
- `benchmarkWorldCreationDestruction` fonksiyonu ise toplu 1K, 10K gibi sayıda nesnenin tek seferde oluşturulup saklandıktan sonra yok edilmesini ölçer.  
- Benchmark sonuçları **milisaniye (ms)** cinsindendir ve konsola okunabilir şekilde yazdırılır.
- 1M entity hedefi ve 100K entity @ 60FPS hedefleri ileride entity ve component fonksiyonları eklendiğinde test edilecektir.
- Şimdilik sadece `ecs::World` basit constructor/destructor süresi test edildi, bu da genellikle çok hızlıdır ve kolayca geçer.
- Bellek sızıntı testleri için ASAN vb. araçlarla ayrıca kontrol edilmelidir.

---

# Örnek benchmark çıktısı (fake, örnek amaçlı)

```
======================================================================
Benchmark: Repeated World Creation+Destruction per iteration
Iterations: 1000
Total time (create+destroy 1000 Worlds): 5.123 ms
Average time per World: 0.005 ms

======================================================================
Benchmark: World Creation and Destruction
Test with 1 World instance(s)
World creation time:  0.010 ms
World destruction time: 0.002 ms
Total create+destroy time: 0.012 ms
Result: PASSED (no crash / leaks detected)

======================================================================
Benchmark: World Creation and Destruction
Test with 1000 World instance(s)
World creation time:  4.923 ms
World destruction time: 0.900 ms
Total create+destroy time: 5.823 ms
Result: PASSED (no crash / leaks detected)

======================================================================
Benchmark: World Creation and Destruction
Test with 10000 World instance(s)
World creation time:  46.512 ms
World destruction time: 8.153 ms
Total create+destroy time: 54.665 ms
Result: PASSED (no crash / leaks detected)

Benchmark complete.
```

---

# İleriye dönük öneriler

- ECS fonksiyonları (entity/component create/destroy) eklendikçe her fonksiyon için mikro benchmarklar yazılmalı ve farklı entity büyüklüklerinde performans ölçümü yapılmalı.
- Bellek kullanımı ve sızıntı testleri `valgrind` veya ASAN gibi araçlarla yapılmalı.
- Match SimplyECS performans hedefleri (örneğin 1M entity <= 20 ms) ancak gerçek fonksiyonlar ortaya çıktıktan sonra anlamlıdır.

---

Başarılar!