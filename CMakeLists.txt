cmake_minimum_required(VERSION 3.20)
project(toy_mlkem LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(toy_mlkem_core
    src/params.cpp
    src/ring.cpp
    src/compress.cpp
    src/cbd.cpp
    src/pke.cpp
    src/features.cpp
    src/stats.cpp
    src/enumerate.cpp)
target_include_directories(toy_mlkem_core PUBLIC include)
if(MSVC)
    target_compile_options(toy_mlkem_core PRIVATE /W4 /permissive- /EHsc)
else()
    target_compile_options(toy_mlkem_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(toy-mlkem src/main.cpp)
target_link_libraries(toy-mlkem PRIVATE toy_mlkem_core)

enable_testing()
add_executable(toy-mlkem-tests tests/tests.cpp)
target_link_libraries(toy-mlkem-tests PRIVATE toy_mlkem_core)
add_test(NAME toy-mlkem-tests COMMAND toy-mlkem-tests)

find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    add_test(NAME python-analysis-tests
             COMMAND ${Python3_EXECUTABLE} -m unittest test_analyze.py -v)
    set_tests_properties(python-analysis-tests PROPERTIES
                         WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/python)
    add_test(NAME frozen-normalized-transfer-tests
             COMMAND ${Python3_EXECUTABLE} -m unittest test_frozen_normalized_transfer.py -v)
    set_tests_properties(frozen-normalized-transfer-tests PROPERTIES
                         WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/python)
    add_test(NAME mechanism-reduction-tests
             COMMAND ${Python3_EXECUTABLE} -m unittest test_mechanism_reduction.py -v)
    set_tests_properties(mechanism-reduction-tests PROPERTIES
                         WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/python)
    add_test(NAME final-su1-confirmation-tests
             COMMAND ${Python3_EXECUTABLE} -m unittest test_final_su1_confirmation.py -v)
    set_tests_properties(final-su1-confirmation-tests PROPERTIES
                         WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/python)
endif()
