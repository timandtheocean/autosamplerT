# AutosamplerT Installation Script for Windows
# Requires PowerShell 5.1 or higher

$ErrorActionPreference = "Stop"
$MIN_PYTHON_VERSION = "3.8"
$RECOMMENDED_PYTHON_VERSION = "3.11"

Write-Host "=== AutosamplerT Installation Script for Windows ===" -ForegroundColor Cyan
Write-Host ""

# Function to compare version numbers
function Compare-Version {
    param([string]$Version1, [string]$Version2)
    $v1 = [version]$Version1
    $v2 = [version]$Version2
    return $v1.CompareTo($v2)
}

# Function to get Python version
function Get-PythonVersion {
    param([string]$PythonCommand)
    try {
        $version = & $PythonCommand --version 2>&1 | Select-String -Pattern "Python (\d+\.\d+\.\d+)" | ForEach-Object { $_.Matches.Groups[1].Value }
        return $version
    } catch {
        return $null
    }
}

# Check for Python installation
Write-Host "Checking for Python installation..." -ForegroundColor Yellow

$pythonCommands = @("python", "python3", "py")
$pythonFound = $false
$pythonCommand = $null
$pythonVersion = $null

foreach ($cmd in $pythonCommands) {
    $version = Get-PythonVersion -PythonCommand $cmd
    if ($version) {
        Write-Host "  Found: $cmd (Python $version)" -ForegroundColor Green
        if ((Compare-Version -Version1 $version -Version2 $MIN_PYTHON_VERSION) -ge 0) {
            $pythonFound = $true
            $pythonCommand = $cmd
            $pythonVersion = $version
            break
        } else {
            Write-Host "  Version $version is too old (minimum: $MIN_PYTHON_VERSION)" -ForegroundColor Red
        }
    }
}

# Install Python if not found or version too old
if (-not $pythonFound) {
    Write-Host ""
    Write-Host "Python $MIN_PYTHON_VERSION or higher not found." -ForegroundColor Red
    Write-Host "Would you like to install Python $RECOMMENDED_PYTHON_VERSION? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host ""
        Write-Host "Installing Python $RECOMMENDED_PYTHON_VERSION..." -ForegroundColor Cyan
        
        # Check if winget is available
        try {
            winget --version | Out-Null
            Write-Host "  Using winget to install Python..." -ForegroundColor Green
            
            # Install Python using winget
            winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
            
            # Refresh PATH
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            
            Write-Host "  Python installed successfully!" -ForegroundColor Green
            Write-Host "  Please close this PowerShell window and run the script again." -ForegroundColor Yellow
            Write-Host ""
            Read-Host "Press Enter to exit"
            exit 0
            
        } catch {
            Write-Host "  winget not available. Opening Python download page..." -ForegroundColor Yellow
            Start-Process "https://www.python.org/downloads/"
            Write-Host ""
            Write-Host "Please install Python $RECOMMENDED_PYTHON_VERSION or higher from the website." -ForegroundColor Yellow
            Write-Host "Make sure to check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
            Write-Host "After installation, run this script again." -ForegroundColor Yellow
            Write-Host ""
            Read-Host "Press Enter to exit"
            exit 0
        }
    } else {
        Write-Host "Installation cancelled." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Using Python $pythonVersion ($pythonCommand)" -ForegroundColor Green

# Check if virtual environment exists
Write-Host ""
Write-Host "Checking for virtual environment..." -ForegroundColor Yellow

if (Test-Path ".venv") {
    Write-Host "  Virtual environment already exists." -ForegroundColor Green
    $recreate = Read-Host "  Recreate it? (Y/N)"
    if ($recreate -eq "Y" -or $recreate -eq "y") {
        Write-Host "  Removing old virtual environment..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv
    } else {
        Write-Host "  Using existing virtual environment." -ForegroundColor Green
    }
}

# Create virtual environment if needed
if (-not (Test-Path ".venv")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    & $pythonCommand -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Virtual environment created successfully!" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
$activateScript = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"

if (Test-Path $activateScript) {
    & $activateScript
    Write-Host "  Virtual environment activated." -ForegroundColor Green
} else {
    Write-Host "  Failed to find activation script!" -ForegroundColor Red
    exit 1
}

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "  pip upgraded." -ForegroundColor Green

# Install requirements
Write-Host ""
Write-Host "Installing Python packages..." -ForegroundColor Yellow

if (Test-Path "REQUIREMENTS.md") {
    Write-Host "  Installing from REQUIREMENTS.md..." -ForegroundColor Cyan
    
    # Extract package names from REQUIREMENTS.md
    $packages = @(
        "numpy",
        "scipy",
        "sounddevice",
        "soundfile",
        "mido",
        "python-rtmidi",
        "pyyaml"
    )
    
    foreach ($package in $packages) {
        Write-Host "    Installing $package..." -ForegroundColor Gray
        python -m pip install $package --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      ✓ $package" -ForegroundColor Green
        } else {
            Write-Host "      ✗ $package (failed)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  REQUIREMENTS.md not found!" -ForegroundColor Red
    exit 1
}

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow

$testScript = @"
import sys
try:
    import numpy
    import scipy
    import sounddevice
    import soundfile
    import mido
    import yaml
    print('SUCCESS')
except ImportError as e:
    print(f'FAILED: {e}')
    sys.exit(1)
"@

$result = python -c $testScript
if ($result -eq "SUCCESS") {
    Write-Host "  All packages installed successfully! ✓" -ForegroundColor Green
} else {
    Write-Host "  Package verification failed: $result" -ForegroundColor Red
    exit 1
}

# Test AutosamplerT
Write-Host ""
Write-Host "Testing AutosamplerT..." -ForegroundColor Yellow
$helpOutput = python autosamplerT.py --help 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  AutosamplerT is working! ✓" -ForegroundColor Green
} else {
    Write-Host "  AutosamplerT test failed!" -ForegroundColor Red
    Write-Host $helpOutput -ForegroundColor Gray
}

# Success message
Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "To use AutosamplerT:" -ForegroundColor Cyan
Write-Host "  1. Activate virtual environment:" -ForegroundColor White
Write-Host "     .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "  2. Run setup:" -ForegroundColor White
Write-Host "     python autosamplerT.py --setup all" -ForegroundColor Gray
Write-Host "  3. Start sampling:" -ForegroundColor White
Write-Host "     python autosamplerT.py --script conf/test/test_single_note.yaml" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation: See DOCUMENTATION.md" -ForegroundColor Cyan
Write-Host ""
