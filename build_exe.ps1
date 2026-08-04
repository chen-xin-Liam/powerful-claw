$ErrorActionPreference = "Continue"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "     AI Computer Control - Build EXE" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$VENV_DIR = "venv"
$APP_FILE = "src/main.py"
$DIST_DIR = "dist"
$BUILD_DIR = "build"
$OUTPUT_NAME = "AIComputerControl"

$VENV_PYTHON = "$VENV_DIR/Scripts/python.exe"
$VENV_PIP = "$VENV_DIR/Scripts/pip.exe"

function Show-ProgressBar {
    param(
        [int]$Current,
        [int]$Total,
        [string]$Message
    )
    $percent = [math]::Round(($Current / $Total) * 100, 0)
    $barLength = 40
    $completed = [math]::Floor(($percent / 100) * $barLength)
    $remaining = $barLength - $completed
    $progressBar = "[" + ("#" * $completed) + ("-" * $remaining) + "]"
    Write-Host -NoNewline "`r$progressBar $percent% - $Message"
}

function Clear-ProgressLine {
    Write-Host -NoNewline "`r" + " " * 80 + "`r"
}

Write-Host "`n[Step 1/5] Checking Virtual Environment" -ForegroundColor Cyan

if (-not (Test-Path $VENV_DIR)) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run start_app.ps1 first to create the virtual environment." -ForegroundColor Yellow
    Read-Host "Press any key to exit"
    exit 1
}

Write-Host "Found virtual environment: $VENV_DIR" -ForegroundColor Green

Write-Host "`n[Step 2/5] Checking PyInstaller" -ForegroundColor Cyan

$pyinstallerInstalled = $false
try {
    & $VENV_PYTHON -c "import PyInstaller; print(PyInstaller.__version__)" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $pyinstallerInstalled = $true
    }
} catch { }

if (-not $pyinstallerInstalled) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    & $VENV_PIP install pyinstaller --disable-pip-version-check 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install PyInstaller!" -ForegroundColor Red
        Read-Host "Press any key to exit"
        exit 1
    }
    
    Write-Host "PyInstaller installed successfully!" -ForegroundColor Green
} else {
    Write-Host "PyInstaller is already installed" -ForegroundColor Green
}

Write-Host "`n[Step 3/5] Cleaning previous builds" -ForegroundColor Cyan

if (Test-Path $DIST_DIR) {
    Write-Host "Removing old dist directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $DIST_DIR | Out-Null
}

if (Test-Path $BUILD_DIR) {
    Write-Host "Removing old build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $BUILD_DIR | Out-Null
}

Write-Host "Clean completed!" -ForegroundColor Green

Write-Host "`n[Step 4/5] Building EXE..." -ForegroundColor Cyan
Write-Host "This may take several minutes..." -ForegroundColor Gray

$pyinstallerArgs = @(
    "--onefile",
    "--console",
    "--name=$OUTPUT_NAME",
    "--distpath=$DIST_DIR",
    "--workpath=$BUILD_DIR",
    "--optimize=2",
    "--strip",
    "--hidden-import=websockets",
    "--hidden-import=soundcard",
    "--hidden-import=cv2",
    "--hidden-import=pyautogui",
    "--hidden-import=keyboard",
    "--hidden-import=customtkinter",
    "--hidden-import=pydantic",
    "--hidden-import=pydantic_settings",
    "--hidden-import=dotenv",
    "--add-data=src/web;web",
    "--add-data=src/web_api;web_api",
    "$APP_FILE"
)

& $VENV_PYTHON -m PyInstaller $pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: Build failed!" -ForegroundColor Red
    Write-Host "Please check the error message above." -ForegroundColor Yellow
    Read-Host "Press any key to exit"
    exit 1
}

Write-Host "`n[Step 5/5] Build completed!" -ForegroundColor Green

$outputPath = Join-Path $DIST_DIR "$OUTPUT_NAME.exe"
if (Test-Path $outputPath) {
    $fileSize = (Get-Item $outputPath).Length / 1MB
    $fileSize = [math]::Round($fileSize, 2)
    
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "Build Successful!" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Output file: $outputPath" -ForegroundColor Yellow
    Write-Host "File size: $fileSize MB" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run the application:" -ForegroundColor Gray
    Write-Host "  $outputPath" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "ERROR: Output file not found!" -ForegroundColor Red
}

Read-Host "Press any key to exit"