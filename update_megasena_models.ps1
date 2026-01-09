# ============================================================
# update_megasena_ls17_v4.ps1
# Pipeline oficial LS17 Mega-Sena v4
# como usar : 	
# ============================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
$BASE_DIR = "C:\Faixabet\V9"
$MEGA_DIR = "$BASE_DIR\modelo_llm_max\loterias\megasena"

$PYTHON = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

$LOG_DIR = "$BASE_DIR\logs"
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE = "$LOG_DIR\update_megasena_ls17_v4_$TIMESTAMP.log"

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
function Log {
    param ([string]$msg)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $LOG_FILE -Value $line
}

function Run-Step {
    param (
        [string]$Title,
        [string]$Cmd
    )

    Log "=================================================="
    Log $Title
    Log "CMD: $Cmd"
    Log "--------------------------------------------------"

    cmd /c "$Cmd" >> $LOG_FILE 2>&1

    if ($LASTEXITCODE -ne 0) {
        Log "ERRO NA ETAPA: $Title"
        Log "PIPELINE ABORTADO"
        exit 1
    }

    Log "ETAPA CONCLUIDA: $Title"
}

# ------------------------------------------------------------
# START
# ------------------------------------------------------------
Log "INICIO PIPELINE LS17 MEGA-SENA V4"
Log "Base: $BASE_DIR"
Log "Mega: $MEGA_DIR"
Log "Python: $PYTHON"

Set-Location $MEGA_DIR

# ------------------------------------------------------------
# 1) PREPARE REAL (v4)
# ------------------------------------------------------------
Run-Step `
    "PREPARE REAL DATA (MS17 v4)" `
    "$PYTHON prepare_real\prepare_real_data_ls17_mega_v3.py"

# ------------------------------------------------------------
# 2) SYNTHETIC PRETRAIN (v4)
# ------------------------------------------------------------
Run-Step `
    "SYNTHETIC PRETRAIN LS17 MEGA V4" `
    "$PYTHON synthetic_pretrain_ls17_mega_v4.py"

# ------------------------------------------------------------
# 3) TRAIN (COM PRETRAIN)
# ------------------------------------------------------------
Run-Step `
    "TRAIN LS17 MEGA V4 (PRETRAIN)" `
    "$PYTHON train\train_ls17_mega_v4.py --pretrain"

# ------------------------------------------------------------
# 4) VALIDATE
# ------------------------------------------------------------
Run-Step `
    "VALIDATE LS17 MEGA V4" `
    "$PYTHON validate\validate_ls17_mega_v4.py"

# ------------------------------------------------------------
# END
# ------------------------------------------------------------
Log "PIPELINE LS17 MEGA-SENA V4 FINALIZADO COM SUCESSO"
Log "LOG SALVO EM: $LOG_FILE"
