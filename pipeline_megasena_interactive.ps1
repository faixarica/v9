# ============================================================
# pipeline_megasena_interactive.ps1
# Pipeline Oficial Interativo – Mega-Sena (LS17+)
# ============================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# CONFIG
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

function Ask-YesNo {
    param ([string]$Question)
    do {
        $ans = Read-Host "$Question (s/n)"
    } while ($ans -notin @("s","n"))
    return $ans -eq "s"
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
        Log "ERRO NA ETAPA: $Title"
        Log "PIPELINE ABORTADO"
        exit 1
    }

    Log "ETAPA OK: $Title"
}

# ------------------------------------------------------------
# START
# ------------------------------------------------------------
Clear-Host
Log "INICIO PIPELINE INTERATIVO MEGA-SENA"
Log "Mega dir: $MEGA_DIR"

if (-not (Test-Path $PYTHON)) {
    Log "ERRO: Python não encontrado"
    exit 1
}

Set-Location $MEGA_DIR

# ------------------------------------------------------------
# MODEL ID
# ------------------------------------------------------------
$modelId = Read-Host "Informe o ID do modelo (ex: 00001)"
Log "MODEL_ID = $modelId"

# ------------------------------------------------------------
# AMBIENTE
# ------------------------------------------------------------
$envMode = Read-Host "Modo de execucao [DEV/PROD]"
Log "AMBIENTE = $envMode"

# ------------------------------------------------------------
# 1) PREPARE REAL (sempre)
# ------------------------------------------------------------
Run-Step `
    "PREPARE REAL DATA" `
    "& `"$PYTHON`" prepare_ms17_v4.py"

# ------------------------------------------------------------
# 2) BASELINE (sempre roda, sem perguntar)
# ------------------------------------------------------------
Run-Step `
    "BASELINE MEGA-SENA" `
    "& `"$PYTHON`" validate\baseline_ms_mega.py"

# ------------------------------------------------------------
# 3) PRÉ-TREINO (PROTEGIDO)
# ------------------------------------------------------------
if (Ask-YesNo "Executar PRE-TREINO sintético?") {

    if (-not (Ask-YesNo "TEM CERTEZA ABSOLUTA? (isso nao deve rodar sempre)")) {
        Log "Pré-treino abortado pelo usuário"
    }
    else {
        Run-Step `
            "PRETRAIN LS17 MEGA (MODEL $modelId)" `
            "& `"$PYTHON`" train\train_ls17_mega_v3.py --pretrain"
    }
}
else {
    Log "Pré-treino ignorado"
}

# ------------------------------------------------------------
# 4) NOVO CONCURSO
# ------------------------------------------------------------
if (-not (Ask-YesNo "Existem novos concursos para treino?")) {
    Log "Sem novos concursos. Treino principal pulado."
    goto VALIDATE
}

# ------------------------------------------------------------
# 5) TREINO PRINCIPAL
# ------------------------------------------------------------
if (Ask-YesNo "Iniciar TREINO do modelo [$modelId]?") {

    Run-Step `
        "TRAIN LS17 MEGA (MODEL $modelId)" `
        "& `"$PYTHON`" train\train_ls17_mega_v3.py --model-id $modelId --env $envMode"
}
else {
    Log "Treino cancelado pelo usuário"
}

# ------------------------------------------------------------
# 6) VALIDAÇÃO (sempre)
# ------------------------------------------------------------
:VALIDATE
Run-Step `
    "VALIDATE LS17 MEGA (MODEL $modelId)" `
    "& `"$PYTHON`" validate\validate_ls17_mega_v3.py --model-id $modelId"

# ------------------------------------------------------------
# END
# ------------------------------------------------------------
Log "PIPELINE FINALIZADO COM SUCESSO"
Log "LOG: $LOG_FILE"
