@echo off
chcp 65001 >nul
echo ============================================================
echo 信息整理Agent系统 - 快速启动
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检查依赖包...
pip show openai >nul 2>&1
if errorlevel 1 (
    echo.
    echo 检测到缺少依赖包，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖包安装失败
        pause
        exit /b 1
    )
    echo.
    echo ✓ 依赖包安装完成
) else (
    echo ✓ 依赖包已安装
)

echo.
echo [2/3] 检查配置...
if not exist .env (
    echo.
    echo [警告] 未找到 .env 配置文件
    echo 请先配置DeepSeek API密钥：
    echo 1. 复制 .env.example 为 .env
    echo 2. 在 .env 中填入你的API密钥
    echo.
    pause
    exit /b 1
)

findstr /C:"DEEPSEEK_API_KEY=sk-" .env >nul
if errorlevel 1 (
    echo.
    echo [警告] API密钥可能未配置
    echo 请在 .env 文件中填入你的DeepSeek API密钥
    echo.
    set /p continue="是否继续运行? (y/n): "
    if /i not "%continue%"=="y" (
        exit /b 0
    )
) else (
    echo ✓ 配置文件存在
)

echo.
echo [3/3] 启动程序...
echo ============================================================
echo.

python main.py

echo.
echo ============================================================
echo 程序已退出
echo ============================================================
pause
