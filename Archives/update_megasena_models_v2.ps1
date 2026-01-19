# ============================================================
# update_megasena_models_v2.ps1
# Pipeline Oficial Mega-Sena – LS17+
#
# REGRAS IMPORTANTES:
# - Pré-treino NÃO roda automaticamente
# - Treino só roda se houver novo concurso
# - Validação sempre roda após treino
# ============================================================

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.Encoding]::UTF8


# ------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------
$BASE_DIR = "C:\Faixabet\V9"
$MEGA_DIR = "$BASE_DIR\modelo_llm_max\loterias\megasena"
$PYTHON   = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

$LOG_DIR = "$BASE_DIR\logs"
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE = "$LOG_DIR\pipeline_megasena_$TIMESTAMP.log"

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
        [string]$Command
    )

    Log "=================================================="
    Log $Title
    Log "CMD: $Command"
    Log "--------------------------------------------------"

    & powershell -NoProfile -Command $Command 2>&1 |
        Tee-Object -FilePath $LOG_FILE -Append

    if ($LASTEXITCODE -ne 0) {
        Log "ERRO: ExitCode $LASTEXITCODE"
        Log "PIPELINE ABORTADO"
        exit 1
    }

    Log "ETAPA OK: $Title"
}

# ------------------------------------------------------------
# START
# ------------------------------------------------------------
Log "INICIO PIPELINE MEGA-SENA (LS17+)"
Log "Base: $BASE_DIR"
Log "Mega: $MEGA_DIR"
Log "Python: $PYTHON"

if (-not (Test-Path $PYTHON)) {
    Log "ERRO: Python não encontrado"
    exit 1
}

Set-Location $MEGA_DIR

# ------------------------------------------------------------
# 1) PREPARAÇÃO DE DADOS (sempre segura)
# ------------------------------------------------------------
Run-Step `
    "PREPARE REAL DATA (MS17)" `
    "& `"$PYTHON`" prepare_ms17_v4.py"

# ------------------------------------------------------------
# 2) CHECAGEM: HOUVE NOVO CONCURSO?
# ------------------------------------------------------------
Run-Step `
    "CHECK NEW CONCURSO (FORCE)" `
    "& `"$PYTHON`" utils\check_new_concurso.py --force"

# exit 100 nunca ocorrerá em FORCE, mas mantemos o contrato
if ($LASTEXITCODE -eq 100) {
    Log "Nenhum novo concurso. Treino pulado."
    goto VALIDATE
}


# ------------------------------------------------------------
# 3) TREINO (SEM PRETRAIN)
# ------------------------------------------------------------
Run-Step `
    "TRAIN MODEL LS17 (REAL DATA ONLY)" `
    "& `"$PYTHON`" train\train_ls17_mega_v3.py"

# ------------------------------------------------------------
# 4) VALIDAÇÃO
# ------------------------------------------------------------
:VALIDATE
Run-Step `
    "VALIDATE MODEL LS17" `
    "& `"$PYTHON`" validate\validate_ls17_mega_v3.py"

# ------------------------------------------------------------
# END
# ------------------------------------------------------------
Log "PIPELINE FINALIZADO COM SUCESSO"
Log "LOG: $LOG_FILE"
