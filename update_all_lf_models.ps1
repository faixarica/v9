# ================++++++++++++===============================================
# execução : powershell -ExecutionPolicy Bypass -File update_all_lf_models.ps1

param(
    [string]$Routine,           # 1,2,3,4
    [switch]$Debug,             # -Debug to enable verbose
    [switch]$Timer,             # -Timer to run in daily loop
    [string]$TimerTime = "20:00", # HH:mm for timer loop
    [switch]$InstallTimer       # -InstallTimer to create scheduled task
)

# ===============================================================
#  FaixaBet - Model Orchestrator (Lotofacil only, stable version)
#  Features:
#    - Logging to file (logs/)
#    - Debug/Verbose mode
#    - Interactive menu OR parameter mode
#    - Daily timer loop (-Timer)
#    - Windows Task Scheduler installer (-InstallTimer)
# ===============================================================

$ErrorActionPreference = "Stop"

# -------------------------
# 1. Paths
# -------------------------
$V8Root        = Split-Path -Parent $MyInvocation.MyCommand.Path
$AdminDir      = Join-Path $V8Root "admin"
$ModelRoot     = Join-Path $V8Root "modelo_llm_max"

$LfRoot        = Join-Path $ModelRoot "loterias\lotofacil"
$LfTrainDir    = Join-Path $LfRoot "train"
$LfBuilder     = Join-Path $LfRoot "build_lf_datasets.py"
$LfTelemetria  = Join-Path $LfRoot "telemetria_lf_models.py"

$RasparScript    = Join-Path $AdminDir "raspar_loteria.py"
$GitUpdateScript = Join-Path $V8Root "update_llm_prod_to_git.ps1"

# -------------------------
# 2. Logging
# -------------------------
$LogsDir = Join-Path $V8Root "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile   = Join-Path $LogsDir "update_all_lf_models_$Timestamp.log"

$Global:DEBUG_MODE = $false

function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$time] [$Level] $Message"
    Add-Content -Path $LogFile -Value $line
}

function Write-Info([string]$msg) {
    Write-Host "[INFO ] $msg" -ForegroundColor Cyan
    Write-Log "INFO" $msg
}
function Write-Ok([string]$msg) {
    Write-Host "[ OK  ] $msg" -ForegroundColor Green
    Write-Log "OK" $msg
}
function Write-ErrorMsg([string]$msg) {
    Write-Host "[ERRO ] $msg" -ForegroundColor Red
    Write-Log "ERRO" $msg
}
function Write-Debug([string]$msg) {
    if ($Global:DEBUG_MODE) {
        Write-Host "[DEBUG] $msg" -ForegroundColor DarkGray
        Write-Log "DEBUG" $msg
    }
}

function Run-Python([string]$scriptPath, [string]$args = "") {
    Write-Info "Running: python $scriptPath $args"
    Write-Debug "Full command: python `"$scriptPath`" $args"

    & python $scriptPath $args
    $exitCode = $LASTEXITCODE

    Write-Debug "Python exit code: $exitCode"

    if ($exitCode -ne 0) {
        Write-ErrorMsg "Failed: $scriptPath (exit code $exitCode)"
        exit 1
    }
}

function Run-IfExists([string]$scriptPath, [ScriptBlock]$action) {
    if (Test-Path $scriptPath) {
        Write-Debug "Found script: $scriptPath"
        & $action
    } else {
        Write-Info "Script not found (skipping): $scriptPath"
    }
}

# -------------------------
# 3. Menu
# -------------------------
function Show-Menu {
    Clear-Host
    Write-Host "==============================================="
    Write-Host "   FaixaBet - Lotofacil Model Orchestrator     "
    Write-Host "==============================================="
    Write-Host "1) Daily routine      (Lotofacil only)"
    Write-Host "2) Weekly routine     (Lotofacil only)"
    Write-Host "3) Bi-weekly routine  (Lotofacil only)"
    Write-Host "4) Monthly routine    (Lotofacil full + telemetry + git)"
    Write-Host "-----------------------------------------------"
    Write-Host "0) Exit"
    Write-Host "==============================================="
}

# -------------------------
# 4. Install Windows scheduled task (Task Scheduler)
# -------------------------
if ($InstallTimer) {
    if (-not $Routine) {
        Write-ErrorMsg "To use -InstallTimer you must also specify -Routine (1,2,3 or 4)."
        exit 1
    }

    $scriptPath = $MyInvocation.MyCommand.Path
    $taskName   = "FaixaBet_UpdateAllModels_Routine$Routine"
    $taskTime   = $TimerTime  # HH:mm

    $taskCmd = "powershell -ExecutionPolicy Bypass -File `"$scriptPath`" -Routine $Routine"

    Write-Info "Creating/updating scheduled task '$taskName' at $taskTime..."
    $arguments = @(
        "/Create",
        "/SC", "DAILY",
        "/TN", $taskName,
        "/TR", $taskCmd,
        "/ST", $taskTime,
        "/F"
    )

    & schtasks.exe @arguments
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Scheduled task '$taskName' created/updated successfully."
        Write-Ok "It will run daily at $taskTime."
        Write-Ok "Command: $taskCmd"
    } else {
        Write-ErrorMsg "Failed to create scheduled task (exit code $LASTEXITCODE)."
    }
    Write-Info "Log file: $LogFile"
    exit
}

# -------------------------
# 5. Routine selection + debug handling
# -------------------------
if (-not $Routine) {
    Show-Menu
    $choice = Read-Host "Choose an option"

    if ($choice -eq "0") {
        Write-Info "Exiting without running routines."
        Write-Log "INFO" "User chose to exit."
        exit
    }

    $Routine = $choice

    $debugChoice = Read-Host "Enable DEBUG/VERBOSE mode? (Y/N)"
    if ($debugChoice -match "^[yY]$") {
        $Global:DEBUG_MODE = $true
        Write-Info "DEBUG mode ENABLED."
    } else {
        Write-Info "DEBUG mode DISABLED."
    }
} else {
    $choice = $Routine
    if ($Debug) {
        $Global:DEBUG_MODE = $true
        Write-Info "DEBUG mode ENABLED by parameter."
    } else {
        Write-Info "DEBUG mode DISABLED (parameter)."
    }
}

Write-Info "Log file: $LogFile"
Write-Debug "V8Root       = $V8Root"
Write-Debug "ModelRoot    = $ModelRoot"
Write-Debug "LfRoot       = $LfRoot"
Write-Debug "LfTrainDir   = $LfTrainDir"
Write-Debug "LfBuilder    = $LfBuilder"
Write-Debug "LfTelemetria = $LfTelemetria"
Write-Debug "RasparScript = $RasparScript"
Write-Debug "GitUpdate    = $GitUpdateScript"
Write-Debug "Timer        = $Timer, TimerTime = $TimerTime"

# -------------------------
# 6. Routine implementation (Lotofacil only)
# -------------------------
function Invoke-Routine([string]$routineCode) {

    switch ($routineCode) {

        "1" {
            Write-Info "Starting DAILY routine (Lotofacil)..."

            Run-IfExists $RasparScript { Run-Python $RasparScript }
            Run-IfExists $LfBuilder   { Run-Python $LfBuilder }

            Run-Python (Join-Path $LfTrainDir "train_ls14.py")
            Run-Python (Join-Path $LfTrainDir "train_ls14pp.py")

            Write-Ok "DAILY routine (Lotofacil) finished."
        }

        "2" {
            Write-Info "Starting WEEKLY routine (Lotofacil)..."

            Run-IfExists $RasparScript { Run-Python $RasparScript }
            Run-IfExists $LfBuilder   { Run-Python $LfBuilder }

            Run-Python (Join-Path $LfTrainDir "train_ls14.py")
            Run-Python (Join-Path $LfTrainDir "train_ls14pp.py")
            Run-Python (Join-Path $LfTrainDir "train_ls15pp.py")

            Write-Ok "WEEKLY routine (Lotofacil) finished."
        }

        "3" {
            Write-Info "Starting BI-WEEKLY routine (Lotofacil)..."

            Run-IfExists $RasparScript { Run-Python $RasparScript }
            Run-IfExists $LfBuilder   { Run-Python $LfBuilder }

            Run-Python (Join-Path $LfTrainDir "train_ls14.py")
            Run-Python (Join-Path $LfTrainDir "train_ls14pp.py")
            Run-Python (Join-Path $LfTrainDir "train_ls15pp.py")
            Run-Python (Join-Path $LfTrainDir "train_ls16.py")
            Run-Python (Join-Path $LfTrainDir "train_ls17_v3.py")

            Write-Ok "BI-WEEKLY routine (Lotofacil) finished."
        }

        "4" {
            Write-Info "Starting MONTHLY routine (Lotofacil full)..."

            Run-IfExists $RasparScript { Run-Python $RasparScript }
            Run-IfExists $LfBuilder   { Run-Python $LfBuilder }

            Run-Python (Join-Path $LfTrainDir "train_ls14.py")
            Run-Python (Join-Path $LfTrainDir "train_ls14pp.py")
            Run-Python (Join-Path $LfTrainDir "train_ls15pp.py")
            Run-Python (Join-Path $LfTrainDir "train_ls16.py")
            Run-Python (Join-Path $LfTrainDir "train_ls17_v3.py")
            Run-Python (Join-Path $LfTrainDir "train_ls18_v3.py")

           # Telemetry (optional)
            Run-IfExists $LfTelemetria { Run-Python $LfTelemetria "--model ls14pp --last_n 500" }
            Run-IfExists $LfTelemetria { Run-Python $LfTelemetria "--model ls15pp --last_n 500" }
            Run-IfExists $LfTelemetria { Run-Python $LfTelemetria "--model ls16   --last_n 500" }
            Run-IfExists $LfTelemetria { Run-Python $LfTelemetria "--model ls17   --last_n 500" }


            # Deploy (optional)
            Run-IfExists $GitUpdateScript {
                Write-Info "Running Git deploy script..."
                & $GitUpdateScript
                if ($LASTEXITCODE -eq 0) {
                    Write-Ok "Git deploy script finished successfully."
                } else {
                    Write-ErrorMsg "Git deploy script failed (exit code $LASTEXITCODE)."
                }
            }

            Write-Ok "MONTHLY routine (Lotofacil) finished."
        }

        Default {
            Write-ErrorMsg "Unknown routine code: $routineCode"
        }
    }
}

# -------------------------
# 7. Timer loop (optional)
# -------------------------
if ($Timer) {
    if (-not $Routine) {
        Write-ErrorMsg "To use -Timer you must also specify -Routine (1,2,3 or 4)."
        exit 1
    }

    Write-Info "TIMER mode ENABLED."
    Write-Info "Routine = $Routine  |  Daily time = $TimerTime"
    Write-Info "Press CTRL+C to stop."
    Write-Info "Log file: $LogFile"

    $lastRunDate = $null

    while ($true) {
        $now = Get-Date
        $currentTime = $now.ToString("HH:mm")

        if ($currentTime -eq $TimerTime -and $lastRunDate -ne $now.Date) {
            Write-Info "Target time ($TimerTime) reached. Running routine $Routine..."
            Invoke-Routine $Routine
            $lastRunDate = $now.Date
            Write-Ok "Routine $Routine executed at $($now.ToString("yyyy-MM-dd HH:mm:ss"))."
        }

        Start-Sleep -Seconds 60
    }
} else {
    Invoke-Routine $Routine
    Write-Ok "Execution finished. Log file: $LogFile"
}
