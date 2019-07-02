include(CMakeFindDependencyMacro)
find_dependency(Boost
    COMPONENTS
        filesystem
        system
        timer
)
find_dependency(Threads)
include("${CMAKE_CURRENT_LIST_DIR}/fern_targets.cmake")
