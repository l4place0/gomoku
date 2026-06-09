cmake_minimum_required(VERSION 3.18)
project(gomoku_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(ENABLE_KATAGOMO_CUDA "Enable KataGomo CUDA direct-link integration" OFF)
set(KATAGOMO_CPP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../KataGomo/cpp")

if(ENABLE_KATAGOMO_CUDA)
  enable_language(CUDA)

  set(KATAGOMO_CORE_SOURCES
    ${KATAGOMO_CPP_DIR}/core/global.cpp
    ${KATAGOMO_CPP_DIR}/core/base64.cpp
    ${KATAGOMO_CPP_DIR}/core/bsearch.cpp
    ${KATAGOMO_CPP_DIR}/core/config_parser.cpp
    ${KATAGOMO_CPP_DIR}/core/datetime.cpp
    ${KATAGOMO_CPP_DIR}/core/elo.cpp
    ${KATAGOMO_CPP_DIR}/core/fancymath.cpp
    ${KATAGOMO_CPP_DIR}/core/fileutils.cpp
    ${KATAGOMO_CPP_DIR}/core/hash.cpp
    ${KATAGOMO_CPP_DIR}/core/logger.cpp
    ${KATAGOMO_CPP_DIR}/core/makedir.cpp
    ${KATAGOMO_CPP_DIR}/core/md5.cpp
    ${KATAGOMO_CPP_DIR}/core/multithread.cpp
    ${KATAGOMO_CPP_DIR}/core/rand.cpp
    ${KATAGOMO_CPP_DIR}/core/rand_helpers.cpp
    ${KATAGOMO_CPP_DIR}/core/sha2.cpp
    ${KATAGOMO_CPP_DIR}/core/test.cpp
    ${KATAGOMO_CPP_DIR}/core/threadsafecounter.cpp
    ${KATAGOMO_CPP_DIR}/core/threadsafequeue.cpp
    ${KATAGOMO_CPP_DIR}/core/threadtest.cpp
    ${KATAGOMO_CPP_DIR}/core/timer.cpp
    ${KATAGOMO_CPP_DIR}/game/board.cpp
    ${KATAGOMO_CPP_DIR}/game/rules.cpp
    ${KATAGOMO_CPP_DIR}/game/gamelogic.cpp
    ${KATAGOMO_CPP_DIR}/game/randomopening.cpp
    ${KATAGOMO_CPP_DIR}/game/boardhistory.cpp
    ${KATAGOMO_CPP_DIR}/game/graphhash.cpp
    ${KATAGOMO_CPP_DIR}/dataio/sgf.cpp
    ${KATAGOMO_CPP_DIR}/dataio/numpywrite.cpp
    ${KATAGOMO_CPP_DIR}/dataio/trainingwrite.cpp
    ${KATAGOMO_CPP_DIR}/dataio/loadmodel.cpp
    ${KATAGOMO_CPP_DIR}/dataio/homedata.cpp
    ${KATAGOMO_CPP_DIR}/dataio/files.cpp
    ${KATAGOMO_CPP_DIR}/dataio/poswriter.cpp
    ${KATAGOMO_CPP_DIR}/neuralnet/nninputs.cpp
    ${KATAGOMO_CPP_DIR}/neuralnet/modelversion.cpp
    ${KATAGOMO_CPP_DIR}/neuralnet/nneval.cpp
    ${KATAGOMO_CPP_DIR}/neuralnet/desc.cpp
    ${KATAGOMO_CPP_DIR}/neuralnet/cudabackend.cpp
    ${KATAGOMO_CPP_DIR}/neuralnet/cudautils.cpp
    ${KATAGOMO_CPP_DIR}/neuralnet/cudahelpers.cu
    ${KATAGOMO_CPP_DIR}/search/timecontrols.cpp
    ${KATAGOMO_CPP_DIR}/search/searchparams.cpp
    ${KATAGOMO_CPP_DIR}/search/mutexpool.cpp
    ${KATAGOMO_CPP_DIR}/search/search.cpp
    ${KATAGOMO_CPP_DIR}/search/searchnode.cpp
    ${KATAGOMO_CPP_DIR}/search/searchresults.cpp
    ${KATAGOMO_CPP_DIR}/search/searchhelpers.cpp
    ${KATAGOMO_CPP_DIR}/search/searchexplorehelpers.cpp
    ${KATAGOMO_CPP_DIR}/search/searchmultithreadhelpers.cpp
    ${KATAGOMO_CPP_DIR}/search/searchnnhelpers.cpp
    ${KATAGOMO_CPP_DIR}/search/searchtimehelpers.cpp
    ${KATAGOMO_CPP_DIR}/search/searchupdatehelpers.cpp
    ${KATAGOMO_CPP_DIR}/search/asyncbot.cpp
    ${KATAGOMO_CPP_DIR}/search/distributiontable.cpp
    ${KATAGOMO_CPP_DIR}/search/localpattern.cpp
    ${KATAGOMO_CPP_DIR}/search/searchnodetable.cpp
    ${KATAGOMO_CPP_DIR}/search/subtreevaluebiastable.cpp
    ${KATAGOMO_CPP_DIR}/search/patternbonustable.cpp
    ${KATAGOMO_CPP_DIR}/search/analysisdata.cpp
    ${KATAGOMO_CPP_DIR}/search/reportedsearchvalues.cpp
    ${KATAGOMO_CPP_DIR}/program/setup.cpp
    ${KATAGOMO_CPP_DIR}/program/playutils.cpp
    ${KATAGOMO_CPP_DIR}/program/playsettings.cpp
    ${KATAGOMO_CPP_DIR}/program/play.cpp
    ${KATAGOMO_CPP_DIR}/program/selfplaymanager.cpp
    ${KATAGOMO_CPP_DIR}/forbiddenPoint/ForbiddenPointFinder.cpp
    ${KATAGOMO_CPP_DIR}/vcfsolver/VCFsolver.cpp
    ${KATAGOMO_CPP_DIR}/vcfsolver/VCFHashTable.cpp
  )

  add_library(katagomo_core STATIC ${KATAGOMO_CORE_SOURCES})
  set_target_properties(katagomo_core PROPERTIES POSITION_INDEPENDENT_CODE ON)
  target_include_directories(katagomo_core PUBLIC
    ${KATAGOMO_CPP_DIR}
    ${KATAGOMO_CPP_DIR}/external
    ${KATAGOMO_CPP_DIR}/external/tclap-1.2.2/include
    ${KATAGOMO_CPP_DIR}/external/filesystem-1.5.8/include
  )
  target_compile_definitions(katagomo_core PUBLIC
    USE_CUDA_BACKEND
    NO_GIT_REVISION
  )
  find_library(LIBZIP_LIBRARY NAMES zip)
  find_path(LIBZIP_INCLUDE_DIR NAMES zip.h)
  if(LIBZIP_LIBRARY AND LIBZIP_INCLUDE_DIR)
    target_include_directories(katagomo_core PUBLIC ${LIBZIP_INCLUDE_DIR})
    target_link_libraries(katagomo_core PUBLIC ${LIBZIP_LIBRARY})
    message(STATUS "Found libzip: ${LIBZIP_LIBRARY}")
  else()
    target_compile_definitions(katagomo_core PUBLIC NO_LIBZIP)
    message(WARNING "libzip not found - selfplay data writing will be disabled")
  endif()
  if(WIN32)
    target_compile_definitions(katagomo_core PUBLIC NOMINMAX BYTE_ORDER=1234 LITTLE_ENDIAN=1234 BIG_ENDIAN=4321 _CRT_SECURE_NO_WARNINGS)
    target_link_libraries(katagomo_core PUBLIC Ws2_32)
  else()
    target_compile_definitions(katagomo_core PUBLIC BYTE_ORDER=__BYTE_ORDER__ LITTLE_ENDIAN=__ORDER_LITTLE_ENDIAN__ BIG_ENDIAN=__ORDER_BIG_ENDIAN__)
    target_link_libraries(katagomo_core PUBLIC pthread)
  endif()

  find_package(CUDAToolkit REQUIRED)

  if(NOT CUDNN_ROOT_DIR AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/include/cuda/include/cudnn.h")
    set(CUDNN_ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/include/cuda" CACHE PATH "Local cuDNN root directory")
  endif()

  find_path(CUDNN_INCLUDE_DIR cudnn.h
    HINTS ${CUDNN_ROOT_DIR} ${CUDAToolkit_INCLUDE_DIRS}
    PATH_SUFFIXES include
  )
  find_library(CUDNN_LIBRARY cudnn
    HINTS ${CUDNN_ROOT_DIR} ${CUDAToolkit_LIBRARY_DIR}
    PATH_SUFFIXES lib lib64 lib/x64
  )
  if(NOT CUDNN_INCLUDE_DIR OR NOT CUDNN_LIBRARY)
    message(FATAL_ERROR "cuDNN not found. Set CUDNN_ROOT_DIR, CUDNN_INCLUDE_DIR, and CUDNN_LIBRARY.")
  endif()
  if(WIN32)
    find_path(CUDNN_BIN_DIR cudnn64_9.dll
      HINTS ${CUDNN_ROOT_DIR}
      PATH_SUFFIXES bin bin/x64
    )
  endif()
  target_include_directories(katagomo_core PUBLIC ${CUDAToolkit_INCLUDE_DIRS} ${CUDNN_INCLUDE_DIR})
  target_link_libraries(katagomo_core PUBLIC CUDA::cublas ${CUDNN_LIBRARY})

  if(WIN32 AND NOT ZLIB_ROOT AND EXISTS "$ENV{USERPROFILE}/scoop/apps/zlib/current/include/zlib.h")
    set(ZLIB_ROOT "$ENV{USERPROFILE}/scoop/apps/zlib/current" CACHE PATH "Local zlib root directory")
  endif()
  find_package(ZLIB REQUIRED)
  target_link_libraries(katagomo_core PUBLIC ZLIB::ZLIB)

  add_executable(KataGomoSelfplay
    src/KataSelfplayMain.cpp
    ${KATAGOMO_CPP_DIR}/command/commandline.cpp
    ${KATAGOMO_CPP_DIR}/command/selfplay.cpp
  )
  target_link_libraries(KataGomoSelfplay PRIVATE katagomo_core)
  set_target_properties(KataGomoSelfplay PROPERTIES
    OUTPUT_NAME "katago"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../KataGomo/scripts/engine"
  )
  if(MSVC)
    target_compile_options(KataGomoSelfplay PRIVATE /W4 /permissive- /utf-8)
  else()
    target_compile_options(KataGomoSelfplay PRIVATE -Wall -Wextra)
  endif()
endif()

set(GAMEENGINE_SOURCES
  src/GameEngineDLL.cpp
  src/KataInferenceAdapter.cpp
)
if(NOT ENABLE_KATAGOMO_CUDA AND EXISTS "${KATAGOMO_CPP_DIR}/forbiddenPoint/ForbiddenPointFinder.cpp")
  list(APPEND GAMEENGINE_SOURCES
    ${KATAGOMO_CPP_DIR}/forbiddenPoint/ForbiddenPointFinder.cpp
  )
endif()

add_library(GameEngine SHARED ${GAMEENGINE_SOURCES})

target_compile_definitions(GameEngine PRIVATE BUILDING_DLL)
target_include_directories(GameEngine PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${KATAGOMO_CPP_DIR}
)

set_target_properties(GameEngine PROPERTIES
  OUTPUT_NAME "GameEngine"
  PREFIX ""
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/lib"
)

if(MSVC)
  target_compile_options(GameEngine PRIVATE /W4 /permissive- /utf-8)
else()
  target_compile_options(GameEngine PRIVATE -Wall -Wextra -fvisibility=hidden)
endif()

if(ENABLE_KATAGOMO_CUDA)
  target_compile_definitions(GameEngine PRIVATE ENABLE_KATAGOMO_CUDA)
  target_link_libraries(GameEngine PRIVATE katagomo_core)
  if(CUDNN_BIN_DIR)
    add_custom_command(TARGET GameEngine POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CUDNN_BIN_DIR}"
        "$<TARGET_FILE_DIR:GameEngine>"
      COMMENT "Copying cuDNN runtime DLLs"
    )
    add_custom_command(TARGET KataGomoSelfplay POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CUDNN_BIN_DIR}"
        "$<TARGET_FILE_DIR:KataGomoSelfplay>"
      COMMENT "Copying cuDNN runtime DLLs for selfplay"
    )
  endif()
  if(CUDAToolkit_BIN_DIR)
    set(KATAGOMO_CUDA_BIN_DIR "${CUDAToolkit_BIN_DIR}")
  elseif(CMAKE_CUDA_COMPILER)
    get_filename_component(KATAGOMO_CUDA_BIN_DIR "${CMAKE_CUDA_COMPILER}" DIRECTORY)
  endif()
  if(KATAGOMO_CUDA_BIN_DIR)
    file(GLOB KATAGOMO_CUDA_RUNTIME_DLLS
      "${KATAGOMO_CUDA_BIN_DIR}/cudart64_*.dll"
      "${KATAGOMO_CUDA_BIN_DIR}/cublas64_*.dll"
      "${KATAGOMO_CUDA_BIN_DIR}/cublasLt64_*.dll"
      "${KATAGOMO_CUDA_BIN_DIR}/x64/cudart64_*.dll"
      "${KATAGOMO_CUDA_BIN_DIR}/x64/cublas64_*.dll"
      "${KATAGOMO_CUDA_BIN_DIR}/x64/cublasLt64_*.dll"
    )
    foreach(cuda_runtime_dll IN LISTS KATAGOMO_CUDA_RUNTIME_DLLS)
      add_custom_command(TARGET GameEngine POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${cuda_runtime_dll}"
          "$<TARGET_FILE_DIR:GameEngine>"
        COMMENT "Copying CUDA runtime DLL ${cuda_runtime_dll}"
      )
      add_custom_command(TARGET KataGomoSelfplay POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${cuda_runtime_dll}"
          "$<TARGET_FILE_DIR:KataGomoSelfplay>"
        COMMENT "Copying CUDA runtime DLL ${cuda_runtime_dll} for selfplay"
      )
    endforeach()
  endif()
  if(ZLIB_ROOT AND EXISTS "${ZLIB_ROOT}/bin/zlib.dll")
    add_custom_command(TARGET GameEngine POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${ZLIB_ROOT}/bin/zlib.dll"
        "$<TARGET_FILE_DIR:GameEngine>"
      COMMENT "Copying zlib runtime DLL"
    )
    add_custom_command(TARGET KataGomoSelfplay POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${ZLIB_ROOT}/bin/zlib.dll"
        "$<TARGET_FILE_DIR:KataGomoSelfplay>"
      COMMENT "Copying zlib runtime DLL for selfplay"
    )
  endif()
endif()
