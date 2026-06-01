cmake_minimum_required(VERSION 3.10)
project(rknn_infer C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# RKNN API 头文件和库
set(RKNN_API_DIR "${CMAKE_CURRENT_SOURCE_DIR}/libs/rknn_api" CACHE PATH "RKNN API path")

if(EXISTS "${RKNN_API_DIR}/include")
    include_directories(${RKNN_API_DIR}/include)
    link_directories(${RKNN_API_DIR}/lib)
else()
    # 系统安装的 RKNN API
    include_directories(/usr/include)
    link_directories(/usr/lib /usr/lib/aarch64-linux-gnu)
endif()

# MPP (Media Process Platform)
include_directories(/usr/include/rockchip)

# RGA (Rockchip Graphics Acceleration)
include_directories(/usr/include/rga)

include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# 编译选项
add_compile_options(-O2 -Wall -Wextra)

# 共享库
add_library(rknn_infer SHARED
    rknn_infer.cpp
    mpp_jpeg_decoder.cpp
    v4l2_camera.cpp
)

target_link_libraries(rknn_infer
    rknnrt           # RKNN推理库
    rockchip_mpp     # MPP媒体处理库
    rga              # RGA图形加速库
    pthread          # 线程库
)

# 安装
install(TARGETS rknn_infer LIBRARY DESTINATION lib)
install(FILES rknn_infer.h mpp_jpeg_decoder.h v4l2_camera.h DESTINATION include)
