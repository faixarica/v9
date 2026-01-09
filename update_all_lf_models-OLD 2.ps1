# ===============================================================
#  FaixaBet - LEGACY Model Orchestrator (Lotofacil ONLY)
#
#  ⚠️ SCRIPT LEGADO (V8)
#  - Usado APENAS para Lotofácil
#  - NÃO inclui Mega-Sena
#  - NÃO usa pipeline V9
#  - Git deploy BLOQUEADO por design
#
#  Status: STABLE / MAINTENANCE MODE
# ===============================================================

param(
    [ValidateSet("1","2","3","4")]
    [string]$Routine,

    [switch]$Debug,
    [switch]$Timer,
    [string]$TimerTime = "20:00",
    [switch]$InstallTimer
)

# -------------------------
# GLOBAL SAFETY FLAGS
# -------------------------
$ErrorActionPreference = "Stop"
$ENABLE_GIT_DEPLOY     = $false     # ⚠️ NÃO ALTERAR
$FAIL_FAST             = $true

# -------------------------
# BASIC ENV VALIDATION
# -------------------------
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[FATAL] Python não encontrado no PATH." -ForegroundColor Red
    exit 1
}

# -------------------------
# ROOT PATH (V9 SAFE)
# -------------------------
if ($PSScriptRoot) {
    $ROOT = $PSScriptRoot
}
elseif ($MyInvocation.MyCommand.Path) {
    $ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
}
else {
    Write-Host "[FATAL] Não foi possível determinar o diretório raiz do script." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] ROOT = $ROOT"

# -------------------------
# MODEL ROOT (PRIVATE)
# -------------------------
if ($env:FAIXABET_MODELS_DIR -and (Test-Path $env:FAIXABET_MODELS_DIR)) {
    $MODEL_ROOT = $env:FAIXABET_MODELS_DIR
}
else {
    $MODEL_ROOT = "C:\Faixabet\modelo_llm_max"
}

Write-Host "[INFO] MODEL_ROOT = $MODEL_ROOT"

# -------------------------
# PROJECT PATHS
# -------------------------
$FAIXABET_ROOT = $ROOT
$ADMIN_DIR     = Join-Path $FAIXABET_ROOT "admin"

$LF_ROOT   = Join-Path $MODEL_ROOT "loterias\lotofacil"
$LF_TRAIN  = Join-Path $LF_ROOT "train"

$SCRAPE_PY = Join-Path $ADMIN_DIR "raspar_loteria.py"
$BUILD_PY  = Join-Path $LF_ROOT "build_lf_datasets.py"
$TELEM_PY  = Join-Path $LF_ROOT "telemetria_lf_models.py"

# -------------------------
# LOGGING (SAFE)
# -------------------------
$LOG_DIR = Join-Path $ROOT "logs"

if (-not (Test-Path $LOG_DIR)) {
    try {
        New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
    }
    catch {
        Write-Host "[FATAL] Falha ao criar diretório de logs: $LOG_DIR" -ForegroundColor Red
        exit 1
    }
}

$STAMP   = Get-Date -Format "yyyyMMdd_HHmmss"
$LOGFILE = Join-Path $LOG_DIR "lf_orchestrator_$STAMP.log"

function Log {
    param([string]$Level, [string]$Msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts][$Level] $Msg"
    Add-Content -Path $LOGFILE -Value $line

    switch ($Level) {
        "INFO"  { Write-Host $line -ForegroundColor Cyan }
        "OK"    { Write-Host $line -ForegroundColor Green }
        "WARN"  { Write-Host $line -ForegroundColor Yellow }
        "ERROR" { Write-Host $line -ForegroundColor Red }
        default { Write-Host $line }
    }
}

# -------------------------
# SAFE EXECUTION
# -------------------------
function Run-Python {
    param([string]$Script)

    if (-not (Test-Path $Script)) {
        Log "WARN" "Script não encontrado, pulando: $Script"
        return
    }

    Log "INFO" "Executando: $Script"
    & python $Script
    $code = $LASTEXITCODE

    if ($code -ne 0) {
        Log "ERROR" "Falha em $Script (exit=$code)"
        if ($FAIL_FAST) { throw "Execução abortada" }
    } else {
        Log "OK" "Finalizado com sucesso: $Script"
    }
}

# -------------------------
# ROUTINES
# -------------------------
function Run-Routine {
    param([string]$R)

    switch ($R) {

        "1" {
            Log "INFO" "ROTINA DIÁRIA (Lotofácil)"
            Run-Python $SCRAPE_PY
            Run-Python $BUILD_PY
            Run-Python (Join-Path $LF_TRAIN "train_ls14.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls14pp.py")
        }

        "2" {
            Log "INFO" "ROTINA SEMANAL (Lotofácil)"
            Run-Python $SCRAPE_PY
            Run-Python $BUILD_PY
            Run-Python (Join-Path $LF_TRAIN "train_ls14.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls14pp.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls15pp.py")
        }

        "3" {
            Log "INFO" "ROTINA QUINZENAL (Lotofácil)"
            Run-Python $SCRAPE_PY
            Run-Python $BUILD_PY
            Run-Python (Join-Path $LF_TRAIN "train_ls14.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls14pp.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls15pp.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls16.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls17_v3.py")
        }

        "4" {
            Log "INFO" "ROTINA MENSAL FULL (Lotofácil)"
            Run-Python $SCRAPE_PY
            Run-Python $BUILD_PY
            Run-Python (Join-Path $LF_TRAIN "train_ls14.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls14pp.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls15pp.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls16.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls17_v3.py")
            Run-Python (Join-Path $LF_TRAIN "train_ls18_v3.py")

            if (Test-Path $TELEM_PY) {
                Log "INFO" "Executando telemetria"
                & python $TELEM_PY --last_n 500
            }

            Log "INFO" "Git deploy BLOQUEADO (LEGACY MODE)"
        }
    }
}

# -------------------------
# TIMER MODE
# -------------------------
if ($Timer) {
    Log "INFO" "TIMER ativo: rotina $Routine às $TimerTime"
    $last = ""

    while ($true) {
        $now = Get-Date
        if ($now.ToString("HH:mm") -eq $TimerTime -and $last -ne $now.Date) {
            Run-Routine $Routine
            $last = $now.Date
        }
        Start-Sleep 60
    }
}
else {
    if (-not $Routine) {
        Write-Host "Escolha a rotina (1-4):"
        Write-Host "1 = Diário | 2 = Semanal | 3 = Quinzenal | 4 = Mensal"
        $Routine = Read-Host "Opção"
    }

    Run-Routine $Routine
    Log "OK" "Execução finalizada. Log: $LOGFILE"
}
