$ErrorActionPreference = "Continue"

$VENV_DIR = "venv"
$REQUIREMENTS_FILE = "requirements.txt"
$PACKAGES_DIR = "packages"
$APP_FILE = "src/main.py"
$PYTHON_MIN_VERSION = "3.10"
$PYTHON_TARGET_VERSION = "3.13"
$PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe"
$PYTHON_INSTALLER_PATH = "$env:TEMP/python-3.13.0-amd64.exe"

$PIP_MIRRORS = @(
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://pypi.douban.com/simple",
    "https://pypi.mirrors.ustc.edu.cn/simple",
    "https://pypi.org/simple"
)

$RUN_ARGS = @(
    "--debug",
    "--port", "15000",
    "--api-port", "15002",
    "--rcon-port", "15001",
    "--monitor-port", "15005",
    "--editor-port", "15010",
    "--theme", "dark",
    "--theme-color", "blue",
    "--log-level", "DEBUG"
)

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

function Test-PythonVersion {
    param([string]$PythonPath)
    try {
        $versionOutput = & $PythonPath --version 2>&1
        if ($LASTEXITCODE -ne 0) { return $null }
        $versionMatch = [regex]::Match($versionOutput, 'Python (\d+\.\d+)')
        if ($versionMatch.Success) {
            return $versionMatch.Groups[1].Value
        }
    } catch { }
    return $null
}

function Is-PythonVersionCompatible {
    param([string]$Version)
    try {
        $currentVersion = [version]$Version
        $minVersion = [version]$PYTHON_MIN_VERSION
        return $currentVersion -ge $minVersion
    } catch {
        return $false
    }
}

function Find-Python {
    Write-Host "`n[Step 1/5] Python Environment Detection" -ForegroundColor Cyan

    $possiblePaths = @(
        "$env:LOCALAPPDATA/Programs/Python/Python$PYTHON_TARGET_VERSION/python.exe",
        "$env:LOCALAPPDATA/Programs/Python/Python${PYTHON_TARGET_VERSION}-amd64/python.exe"
    )

    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $version = Test-PythonVersion $path
            if ($version -and (Is-PythonVersionCompatible $version)) {
                Write-Host "Found compatible Python $version at: $path" -ForegroundColor Green
                return $path
            }
        }
    }

    try {
        $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($pythonPath) {
            $version = Test-PythonVersion $pythonPath
            if ($version) {
                if (Is-PythonVersionCompatible $version) {
                    Write-Host "Found compatible Python $version at: $pythonPath" -ForegroundColor Green
                    return $pythonPath
                } else {
                    Write-Host "Found Python $version but version is too old (requires >= $PYTHON_MIN_VERSION)" -ForegroundColor Yellow
                }
            }
        }
    } catch { }

    return $null
}

function Install-Python {
    Write-Host "`nPython not found or version incompatible! Starting automatic installation..." -ForegroundColor Yellow
    $confirm = Read-Host "Install Python $PYTHON_TARGET_VERSION? (Y/N)"
    if ($confirm.ToUpper() -ne "Y") {
        Write-Host "Installation cancelled." -ForegroundColor Red
        exit 1
    }

    Write-Host "Downloading Python installer..." -ForegroundColor Cyan
    (New-Object System.Net.WebClient).DownloadFile($PYTHON_INSTALLER_URL, $PYTHON_INSTALLER_PATH)

    Write-Host "Installing Python..." -ForegroundColor Cyan
    $process = Start-Process -FilePath $PYTHON_INSTALLER_PATH -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait -PassThru -NoNewWindow

    if ($process.ExitCode -ne 0) {
        Write-Host "Python installation failed!" -ForegroundColor Red
        exit 1
    }

    $installedPython = "$env:LOCALAPPDATA/Programs/Python/Python$PYTHON_TARGET_VERSION/python.exe"
    Write-Host "Python installed successfully: $installedPython" -ForegroundColor Green
    return $installedPython
}

function Get-Installed-Packages {
    param($VenvPip)
    $installed = @{}
    
    try {
        $output = & $VenvPip list --format=freeze 2>&1
        if ($LASTEXITCODE -eq 0) {
            foreach ($line in $output) {
                if ($line -match '^([a-zA-Z0-9_-]+)==([0-9.]+)') {
                    $name = $matches[1].ToLower()
                    $version = $matches[2]
                    $installed[$name] = $version
                }
            }
        }
    } catch { }
    
    return $installed
}

function Parse-Requirement {
    param([string]$Req)
    $req = $Req.Trim()
    if (-not $req -or $req.StartsWith('#')) {
        return $null
    }
    
    $name = $null
    $specifier = $null
    
    if ($req -match '^([a-zA-Z0-9_-]+)(.*)') {
        $name = $matches[1].ToLower()
        $specifier = $matches[2].Trim()
    }
    
    return @{ Name = $name; Specifier = $specifier }
}

function Test-Package-Installed {
    param($InstalledPackages, $PackageName, $Specifier)
    $pkgName = $PackageName.ToLower()
    
    if (-not $InstalledPackages.ContainsKey($pkgName)) {
        return $false
    }
    
    if (-not $Specifier) {
        return $true
    }
    
    $installedVersion = $InstalledPackages[$pkgName]
    
    if ($Specifier -match '==([0-9.]+)') {
        return $installedVersion -eq $matches[1]
    }
    
    try {
        $installedVer = [version]($installedVersion.TrimEnd('.'))
        if ($Specifier -match '>=([0-9.]+)') {
            $requiredVer = [version]($matches[1].TrimEnd('.'))
            return $installedVer -ge $requiredVer
        }
        
        if ($Specifier -match '>\s*([0-9.]+)') {
            $requiredVer = [version]($matches[1].TrimEnd('.'))
            return $installedVer -gt $requiredVer
        }
        
        if ($Specifier -match '<=([0-9.]+)') {
            $requiredVer = [version]($matches[1].TrimEnd('.'))
            return $installedVer -le $requiredVer
        }
        
        if ($Specifier -match '<\s*([0-9.]+)') {
            $requiredVer = [version]($matches[1].TrimEnd('.'))
            return $installedVer -lt $requiredVer
        }
    } catch {
        Write-Host "WARNING: Version comparison failed for $PackageName" -ForegroundColor Yellow
    }
    
    return $true
}

function Get-Missing-Dependencies {
    param($VenvPip, $RequirementsFile)
    
    if (-not (Test-Path $RequirementsFile)) {
        Write-Host "WARNING: $RequirementsFile not found!" -ForegroundColor Yellow
        return @()
    }
    
    $installedPackages = Get-Installed-Packages $VenvPip
    $missing = @()
    
    foreach ($line in Get-Content $RequirementsFile) {
        $parsed = Parse-Requirement $line
        if (-not $parsed) {
            continue
        }
        
        if (-not (Test-Package-Installed $installedPackages $parsed.Name $parsed.Specifier)) {
            $missing += $line
        }
    }
    
    return $missing
}

function Download-Package {
    param($VenvPip, $Package, $DestDir)
    $packageName = $Package -split '[=<>~]' | Select-Object -First 1
    
    foreach ($mirror in $PIP_MIRRORS) {
        & $VenvPip download $Package --dest $DestDir --index-url $mirror --no-deps --disable-pip-version-check 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    }
    
    return $false
}

function Install-Dependencies-Smart {
    param($VenvPip, $RequirementsFile)

    Write-Host "`n[Step 3/5] Checking Dependencies" -ForegroundColor Cyan

    if (-not (Test-Path $RequirementsFile)) {
        Write-Host "WARNING: $RequirementsFile not found!" -ForegroundColor Yellow
        return
    }

    $missing = Get-Missing-Dependencies $VenvPip $RequirementsFile
    $totalMissing = $missing.Count

    if ($totalMissing -eq 0) {
        Write-Host "All dependencies are already installed!" -ForegroundColor Green
        return
    }

    Write-Host "Found $totalMissing missing packages. Starting installation..." -ForegroundColor Cyan

    if (-not (Test-Path $PACKAGES_DIR)) {
        New-Item -ItemType Directory -Path $PACKAGES_DIR -Force | Out-Null
        Write-Host "Created packages directory: $PACKAGES_DIR" -ForegroundColor Green
    }

    $currentPackage = 0
    foreach ($req in $missing) {
        $currentPackage++
        $packageName = $req -split '[=<>~]' | Select-Object -First 1

        Show-ProgressBar -Current $currentPackage -Total $totalMissing -Message "Installing $packageName..."

        $downloaded = $false
        
        foreach ($mirror in $PIP_MIRRORS) {
            & $VenvPip install $req --index-url $mirror --disable-pip-version-check 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $downloaded = $true
                break
            }
        }

        Clear-ProgressLine

        if (-not $downloaded) {
            Write-Host "WARNING: Failed to install $packageName" -ForegroundColor Yellow
        }
    }

    Write-Host "Dependency installation completed!" -ForegroundColor Green
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "     AI Computer Control" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

$SYSTEM_PYTHON = Find-Python

if (-not $SYSTEM_PYTHON) {
    $SYSTEM_PYTHON = Install-Python
}

Write-Host "`n[Step 2/5] Creating/Using Virtual Environment" -ForegroundColor Cyan

if (-not (Test-Path $VENV_DIR)) {
    Write-Host "Creating new virtual environment..." -ForegroundColor Yellow
    & $SYSTEM_PYTHON -m venv $VENV_DIR
} else {
    Write-Host "Using existing virtual environment" -ForegroundColor Green
}

$VENV_PYTHON = "$VENV_DIR/Scripts/python.exe"
$VENV_PIP = "$VENV_DIR/Scripts/pip.exe"

Install-Dependencies-Smart -VenvPip $VENV_PIP -RequirementsFile $REQUIREMENTS_FILE

Write-Host "`n[Step 4/5] Starting Application" -ForegroundColor Cyan
Write-Host "Using: $VENV_PYTHON" -ForegroundColor Green
Write-Host ""

& $VENV_PYTHON "$APP_FILE" $RUN_ARGS