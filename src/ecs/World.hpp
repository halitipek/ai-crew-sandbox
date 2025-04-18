File: src/ecs/World.hpp

```cpp
#pragma once

namespace ecs {

/**
 * @brief The World class is the entry point of the ECS system.
 *
 * World is responsible for managing entities and their components.
 * At this MVP stage it only provides a default constructor and
 * destructor. Future methods for entity creation, destruction,
 * component storage, iteration, etc., will be added here.
 */
class World {
public:
    /**
     * @brief Construct a new, empty World.
     *
     * Initializes all internal data structures. At this point,
     * the world contains no entities or components.
     */
    World();

    /**
     * @brief Destroy the World.
     *
     * Cleans up all allocated resources. Any remaining entities
     * and their components will be destroyed.
     */
    ~World();

    // --------------------------------------------------------------------
    // Future interface (stubs):
    //
    // std::uint32_t createEntity();
    // void destroyEntity(std::uint32_t entity);
    // template<typename Component, typename... Args>
    // void addComponent(std::uint32_t entity, Args&&... args);
    // template<typename Component>
    // bool hasComponent(std::uint32_t entity) const;
    // template<typename Component>
    // Component& getComponent(std::uint32_t entity);
    // --------------------------------------------------------------------
};

} // namespace ecs
```