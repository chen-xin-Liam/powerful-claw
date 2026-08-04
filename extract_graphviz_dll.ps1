$ErrorActionPreference = "Continue"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "     Graphviz DLL 提取工具" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$TEMP_DIR = "$env:TEMP\graphviz_extract"
$OUTPUT_DIR = "venv\Lib\site-packages\graphviz_dll"
$GRAPHVIZ_ZIP = "$TEMP_DIR\graphviz.zip"
$GRAPHVIZ_URL = "https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-windows/12.2.1/win32.zip"

Write-Host "`n[Step 1/4] 创建临时目录" -ForegroundColor Cyan
if (Test-Path $TEMP_DIR) {
    Remove-Item -Recurse -Force $TEMP_DIR | Out-Null
}
New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null
Write-Host "临时目录已创建: $TEMP_DIR" -ForegroundColor Green

Write-Host "`n[Step 2/4] 下载 Graphviz 便携版" -ForegroundColor Cyan
Write-Host "下载地址: $GRAPHVIZ_URL" -ForegroundColor Gray

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $GRAPHVIZ_URL -OutFile $GRAPHVIZ_ZIP -TimeoutSec 300 -UseBasicParsing
    Write-Host "下载完成!" -ForegroundColor Green
} catch {
    Write-Host "下载失败: $_" -ForegroundColor Red
    Write-Host "尝试使用备用地址..." -ForegroundColor Yellow
    $ALT_URL = "https://github.com/graphviz-dev/graphviz/releases/download/12.2.1/graphviz-windows-x64.zip"
    try {
        Invoke-WebRequest -Uri $ALT_URL -OutFile $GRAPHVIZ_ZIP -TimeoutSec 300 -UseBasicParsing
        Write-Host "备用下载完成!" -ForegroundColor Green
    } catch {
        Write-Host "备用下载也失败" -ForegroundColor Red
        Write-Host "请手动下载 Graphviz: https://graphviz.org/download/" -ForegroundColor Yellow
        Read-Host "按任意键退出"
        exit 1
    }
}

Write-Host "`n[Step 3/4] 解压文件" -ForegroundColor Cyan
Expand-Archive -Path $GRAPHVIZ_ZIP -DestinationPath $TEMP_DIR -Force
Write-Host "解压完成!" -ForegroundColor Green

Write-Host "`n[Step 4/4] 提取 DLL 文件" -ForegroundColor Cyan

if (Test-Path $OUTPUT_DIR) {
    Remove-Item -Recurse -Force $OUTPUT_DIR | Out-Null
}
New-Item -ItemType Directory -Path $OUTPUT_DIR -Force | Out-Null

$sourceDir = $TEMP_DIR
$foundDlls = @()

Get-ChildItem -Path $sourceDir -Filter "*.dll" -Recurse | ForEach-Object {
    $dllPath = $_.FullName
    $dllName = $_.Name
    $destPath = Join-Path $OUTPUT_DIR $dllName

    Write-Host "  找到: $dllName" -ForegroundColor Gray
    Copy-Item -Path $dllPath -Destination $destPath -Force
    $foundDlls += $dllName
}

if ($foundDlls.Count -eq 0) {
    Write-Host "警告: 未找到 DLL 文件，尝试查找其他文件..." -ForegroundColor Yellow
    Get-ChildItem -Path $sourceDir -Recurse | Select-Object -First 20 | ForEach-Object {
        Write-Host "  文件: $($_.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "`n成功提取 $($foundDlls.Count) 个 DLL 文件!" -ForegroundColor Green
    Write-Host "输出目录: $OUTPUT_DIR" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "DLL 文件列表:" -ForegroundColor Cyan
    foreach ($dll in $foundDlls) {
        Write-Host "  - $dll" -ForegroundColor White
    }
}

Write-Host "`n清理临时文件..." -ForegroundColor Cyan
Remove-Item -Recurse -Force $TEMP_DIR -ErrorAction SilentlyContinue
Write-Host "清理完成!" -ForegroundColor Green

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "DLL 提取完成!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "现在可以安装 pygraphviz:" -ForegroundColor Yellow
Write-Host "  pip install pygraphviz" -ForegroundColor White
Write-Host ""
Write-Host "或者将 DLL 目录添加到系统 PATH:" -ForegroundColor Yellow
Write-Host "  $OUTPUT_DIR" -ForegroundColor White
Write-Host ""

Read-Host "按任意键退出"