@echo off
setlocal

set BUILD_DIR=build
set CONFIG=Release
set CMAKE_GENERATOR=
set FORCE_VS_GENERATOR=0
set REQUESTED_GENERATOR=Visual Studio 17 2022

echo %* | findstr /I "ENABLE_KATAGOMO_CUDA=ON" >nul 2>nul
if not errorlevel 1 set FORCE_VS_GENERATOR=1

if "%FORCE_VS_GENERATOR%"=="1" (
  where nmake >nul 2>nul
  if not errorlevel 1 set CMAKE_GENERATOR=NMake Makefiles
)

if "%FORCE_VS_GENERATOR%"=="0" (
  where ninja >nul 2>nul
  if not errorlevel 1 set CMAKE_GENERATOR=Ninja

  if "%CMAKE_GENERATOR%"=="" (
    where mingw32-make >nul 2>nul
    if not errorlevel 1 set CMAKE_GENERATOR=MinGW Makefiles
  )

  if "%CMAKE_GENERATOR%"=="" (
    where make >nul 2>nul
    if not errorlevel 1 set CMAKE_GENERATOR=Unix Makefiles
  )
)

if not "%CMAKE_GENERATOR%"=="" set REQUESTED_GENERATOR=%CMAKE_GENERATOR%
if exist "%BUILD_DIR%\CMakeCache.txt" (
  findstr /C:"CMAKE_GENERATOR:INTERNAL=%REQUESTED_GENERATOR%" "%BUILD_DIR%\CMakeCache.txt" >nul 2>nul
  if errorlevel 1 rmdir /s /q "%BUILD_DIR%"
)
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

if "%CMAKE_GENERATOR%"=="" (
  cmake -S . -B "%BUILD_DIR%" -G "Visual Studio 17 2022" -A x64 %*
) else (
  cmake -S . -B "%BUILD_DIR%" -G "%CMAKE_GENERATOR%" -DCMAKE_BUILD_TYPE=%CONFIG% %*
)
if errorlevel 1 exit /b %errorlevel%

cmake --build "%BUILD_DIR%" --config %CONFIG%
if errorlevel 1 exit /b %errorlevel%

echo Built GameEngine.dll
