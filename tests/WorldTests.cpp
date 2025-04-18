```cpp
// File: tests/WorldTests.cpp

#include <gtest/gtest.h>
#include "src/ecs/World.hpp"

// Note:
// Currently, ecs::World only has default ctor and dtor and no member functions or state to verify.
// Therefore tests are limited to object lifetime and resource management checks.
// Future extension tests should be added as new functionalities appear.

namespace ecs {
namespace test {

// --- Fixture for World related tests ---
class WorldTest : public ::testing::Test {
protected:
    // Setup before each test
    void SetUp() override {
        // No setup needed currently
    }

    // Cleanup after each test
    void TearDown() override {
        // No cleanup needed currently
    }
};

// Test default construction should create a valid World object
TEST_F(WorldTest, DefaultConstructor_CreatesWorldInstance) {
    // Arrange & Act
    World world;

    // Assert
    // No direct internal state to verify.
    // If construction throws, test fails.
    SUCCEED() << "World default constructor completed without throwing.";
}

// Test destruction does not cause crashes or leaks (implicitly tested by Valgrind etc.)
TEST_F(WorldTest, Destructor_CleansUpWithoutCrash) {
    // Arrange: create a scope to force stack destruction
    {
        World world;
        // nothing to setup or verify internally
    }
    // If destructor causes crash, test runner will fail.
    SUCCEED() << "World destructor completed without crashing.";
}

// Test multiple World instances can coexist and destruct independent of each other.
TEST_F(WorldTest, MultipleInstances_CreateAndDestroySafely) {
    // Arrange & Act
    World w1;
    World w2;
    World w3;

    // Assert
    // Confirm all instances constructed - if any constructor throws, test fails earlier.
    SUCCEED() << "Multiple World instances created and exist simultaneously.";

    // Instances destructed at end of scope automatically.
}

// Test default copy constructor and assignment (allowed as per current header)
// Verify World can be copy-constructed and copy-assigned (shallow copies likely).
TEST_F(WorldTest, CopyConstructor_WorksAsExpected) {
    World original;

    // Act
    World copy(original);

    // Assert
    SUCCEED() << "World copy constructor invoked without error.";
}

// Test copy assignment operator behavior
TEST_F(WorldTest, CopyAssignmentOperator_WorksAsExpected) {
    World w1;
    World w2;

    // Act
    w1 = w2;

    // Assert
    SUCCEED() << "World copy assignment operator invoked without error.";
}

// Test move constructor and move assignment operator usage (defaulted)
TEST_F(WorldTest, MoveConstructor_WorksAsExpected) {
    World original;

    // Act
    World moved(std::move(original));

    // Assert
    SUCCEED() << "World move constructor invoked without error.";
}

TEST_F(WorldTest, MoveAssignmentOperator_WorksAsExpected) {
    World w1;
    World w2;

    // Act
    w1 = std::move(w2);

    // Assert
    SUCCEED() << "World move assignment operator invoked without error.";
}

// Edge case: create and destroy a large number of World instances in a loop
TEST_F(WorldTest, MassCreationAndDestruction_DoesNotLeakOrCrash) {
    constexpr int largeCount = 10000;

    for (int i = 0; i < largeCount; ++i) {
        World w;
        (void)w; // suppress unused warning
    }

    SUCCEED() << "Created and destroyed " << largeCount << " World instances without error.";
}

// Edge case: Nested World instances in scopes
TEST_F(WorldTest, NestedScopeInstances_ConstructAndDestructProperly) {
    {
        World w1;
        {
            World w2;
            {
                World w3;
            } // w3 destroyed here
        } // w2 destroyed here
    } // w1 destroyed here

    SUCCEED() << "Nested World instances constructed and destructed properly.";
}

} // namespace test
} // namespace ecs
```