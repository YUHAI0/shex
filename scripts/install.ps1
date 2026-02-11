<#
.SYNOPSIS
    Installs Shex CLI tool on Windows.
.DESCRIPTION
    This script installs Shex and its dependencies. It also updates the source code if run within a git repository.
#>

$ErrorActionPreference = "Stop"

Write-Host "Starting Shex installation..." -ForegroundColor Cyan

# Determine installation mode (Local or Remote)
$isLocal = $false
if (Test-Path "..\pyproject.toml") {
    Set-Location ..
    $isLocal = $true
} elseif (Test-Path "pyproject.toml") {
    $isLocal = $true
}

# Check for Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.8+ from https://www.python.org/downloads/"
    exit 1
}

if ($isLocal) {
    # Update source code if git repo
    if (Test-Path ".git") {
        Write-Host "Updating source code from git..." -ForegroundColor Cyan
        try {
            git pull
        } catch {
            Write-Warning "Failed to update source code. Proceeding with current version."
        }
    }
    
    # Install/Upgrade Shex from local source
    Write-Host "Installing/Updating Shex from local source..." -ForegroundColor Cyan
    try {
        python -m pip install --upgrade pip setuptools wheel
        python -m pip install --upgrade .
    } catch {
        Write-Error "Installation failed. Please check the error messages above."
        exit 1
    }
} else {
    # Remote installation from GitHub
    Write-Host "Installing/Updating Shex from GitHub..." -ForegroundColor Cyan
    try {
        python -m pip install --upgrade pip setuptools wheel
        # Install directly from the main branch archive
        python -m pip install --upgrade https://github.com/YUHAI0/shex/archive/master.zip
    } catch {
        Write-Error "Installation failed. Please check the error messages above."
        exit 1
    }
}

# Verify installation
if (Get-Command shex -ErrorAction SilentlyContinue) {
    Write-Host "Shex installed successfully!" -ForegroundColor Green
    Write-Host "You can now run 'shex' from the command line." -ForegroundColor Green
    try {
        shex --version
    } catch {
        # Ignore version check error if command fails for some reason
    }
} else {
    Write-Warning "Shex installed but 'shex' command not found in PATH."
    
    # Try to find where it is installed
    try {
        # Get potential installation directories (System and User)
        $pyCmd = "import sys; import sysconfig; import os; print(os.path.join(sys.prefix, 'Scripts') + '|' + sysconfig.get_path('scripts', 'nt_user'))"
        $paths = python -c $pyCmd
        $candidateDirs = $paths -split "\|"
        
        $scriptsDir = $null
        foreach ($dir in $candidateDirs) {
            # Trim whitespace just in case
            $dir = $dir.Trim()
            if (Test-Path "$dir\shex.exe") {
                $scriptsDir = $dir
                break
            }
        }

        if ($scriptsDir) {
            Write-Host "Found executable at: $scriptsDir\shex.exe" -ForegroundColor Yellow
            
            # Check if already in PATH (User scope)
            $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($userPath -notlike "*$scriptsDir*") {
                Write-Host "Adding '$scriptsDir' to User PATH..." -ForegroundColor Cyan
                $newPath = "$userPath;$scriptsDir"
                [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
                $env:PATH = "$env:PATH;$scriptsDir"
                Write-Host "Added to PATH. You may need to restart your terminal for changes to take effect permanently." -ForegroundColor Green
            } else {
                Write-Host "'$scriptsDir' is already in User PATH." -ForegroundColor Gray
            }
        } else {
            Write-Warning "Could not find shex.exe in standard Python script locations."
        }
    } catch {
        Write-Warning "Could not determine installation directory or add to PATH."
    }
}

Write-Host "Installation complete." -ForegroundColor Cyan
