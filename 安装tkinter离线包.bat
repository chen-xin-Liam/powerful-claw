@echo off
chcp 65001 >nul
echo ==============================================
echo      Tkinter 离线安装脚本
echo      For 嵌入式 Python
echo ==============================================
echo.
echo 正在从系统 Python 3.13 复制 tkinter 文件...
echo 这可能需要几分钟时间...
echo.

set "SRC=%LOCALAPPDATA%\Programs\Python\Python313"
set "DST=%CD%\pythonembed"

if not exist "%SRC%\python.exe" (
    echo 错误: 未找到系统 Python 3.13!
    echo 请先安装 Python 3.13
    pause
    exit /b 1
)

echo 步骤 1/4: 复制 DLL 文件...
if not exist "%DST%\DLLs" mkdir "%DST%\DLLs"
copy /Y "%SRC%\DLLs\_tkinter.pyd" "%DST%\" >nul
copy /Y "%SRC%\DLLs\tcl86t.dll" "%DST%\" >nul
copy /Y "%SRC%\DLLs\tk86t.dll" "%DST%\" >nul

echo 步骤 2/4: 复制 Python 扩展...
for %%F in (_tkinter.pyd _ctypes.pyd _asyncio.pyd _socket.pyd _ssl.pyd) do (
    if exist "%SRC%\DLLs\%%F" copy /Y "%SRC%\DLLs\%%F" "%DST%\" >nul
)

echo 步骤 3/4: 复制 tkinter 模块...
if not exist "%DST%\Lib\tkinter" mkdir "%DST%\Lib\tkinter"
xcopy /E /Y "%SRC%\Lib\tkinter" "%DST%\Lib\tkinter\" >nul

echo 步骤 4/4: 复制 tcl 运行时...
if not exist "%DST%\tcl" mkdir "%DST%\tcl"
xcopy /E /Y "%SRC%\tcl" "%DST%\tcl\" >nul

echo.
echo ==============================================
echo 安装完成！正在测试...
echo ==============================================

set TCL_LIBRARY=%DST%\tcl\tcl8.6
set TK_LIBRARY=%DST%\tcl\tk8.6

"%DST%\python.exe" -c "import tkinter; print('成功! tkinter 版本:', tkinter.TkVersion)"

if %errorlevel% neq 0 (
    echo.
    echo 测试失败。请检查错误信息。
) else (
    echo.
    echo tkinter 安装成功！
)

echo.
pause
