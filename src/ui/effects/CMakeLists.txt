cmake_minimum_required(VERSION 3.16)

project(gl_effects VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

if(WIN32)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /O2 /DNDEBUG")
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} /SUBSYSTEM:WINDOWS")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -DNDEBUG -fPIC")
endif()

find_package(OpenGL REQUIRED)

add_library(gl_effects SHARED
    gl_effects.cpp
    gl_effects.h
)

target_link_libraries(gl_effects PRIVATE ${OPENGL_LIBRARIES})

target_include_directories(gl_effects PRIVATE ${OPENGL_INCLUDE_DIR})

if(WIN32)
    target_link_libraries(gl_effects PRIVATE opengl32)
else()
    target_link_libraries(gl_effects PRIVATE GL GLU)
endif()

set_target_properties(gl_effects PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
    PUBLIC_HEADER gl_effects.h
)

install(TARGETS gl_effects
    LIBRARY DESTINATION lib
    PUBLIC_HEADER DESTINATION include
)