# ============================================================
# update_megasena_ls17_v4.ps1
# Pipeline LS17 Mega-Sena v4
# Versão GOVERNADA / SEGURA / AUDITÁVEL
# ============================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# CONFIGURAÇÃO GERAL
# ------------------------------------------------------------
$BASE_DIR = "C:\Faixabet\V9"
$MEGA_DIR = "$BASE_DIR\modelo_llm_max\loterias\megasena"
$PYTHON   = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

$LOG_DIR = "$BASE_DIR\logs"
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE  = "$LOG_DIR\update_megasena_ls17_v4_$TIMESTAMP.log"

# MARCADOR DE ESTADO DO MODELO
$PRETRAIN_MARK = "$MEGA_DIR\models\ls17_pretrain.done"

# ------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ------------------------------------------------------------
function Log {
    param ([string]$msg)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $LOG_FILE -Value $line
}

function Abort {
    param ([string]$msg)
    Log "ABORTADO: $msg"
    Log "PIPELINE ENCERRADO SEM TREINO"
    exit 1
}

function Run-Step {
    param (
        [string]$Title,
        [string[]]$Cmd,
        [string]$WorkDir
    )

    Log "=================================================="
    Log "ETAPA: $Title"
    Log "CMD  : $($Cmd -join ' ')"
    Log "DIR  : $WorkDir"
    Log "--------------------------------------------------"

    try {
        Push-Location $WorkDir
        & $Cmd[0] $Cmd[1..($Cmd.Length - 1)] 2>&1 |
            Tee-Object -FilePath $LOG_FILE -Append

        if ($LASTEXITCODE -ne 0) {
            throw "ExitCode diferente de zero: $LASTEXITCODE"
        }

        Log "ETAPA CONCLUIDA COM SUCESSO"
    }
    catch {
        Log "ERRO NA ETAPA"
        Log "DETALHE: $_"
        Abort "Falha crítica em $Title"
    }
    finally {
        Pop-Location
    }
}

# ------------------------------------------------------------
# INÍCIO DO PIPELINE
# ------------------------------------------------------------
Log "INICIO PIPELINE LS17 MEGA-SENA V4"
Log "Base Dir : $BASE_DIR"
Log "Mega Dir : $MEGA_DIR"
Log "Python   : $PYTHON"

if (-not (Test-Path $PYTHON)) {
    Abort "Python não encontrado"
}

# ------------------------------------------------------------
# ETAPA 0 — EXPLICAÇÃO FORMAL (REGISTRADA EM LOG)
# ------------------------------------------------------------
Log "CHECK DE GOVERNANÇA — LEIA COM ATENÇÃO"
Log "Pergunta 1: O encoder, flatten ou features mudaram?"
Log " - Exemplo de SIM : alteração em prepare_ms17_v4.py"
Log " - Exemplo de NÃO: apenas novos concursos"
Log ""
Log "Pergunta 2: O modelo sintético mudou estruturalmente?"
Log " - Exemplo de SIM : nova lógica de geração"
Log " - Exemplo de NÃO: apenas mais amostras"
Log ""
Log "Regra: Se QUALQUER resposta for SIM, pré-treino é obrigatório."
Log "Regra: Caso contrário, pré-treino é PROIBIDO."
Log ""

# ------------------------------------------------------------
# ETAPA 1 — PREPARE REAL
# ------------------------------------------------------------
Run-Step `
    "PREPARE REAL DATA (MS17 v4)" `
    @($PYTHON, "prepare_ms17_v4.py") `
    $MEGA_DIR

# ------------------------------------------------------------
# ETAPA 2 — DECISÃO DE PRÉ-TREINO
# ------------------------------------------------------------
if (-not (Test-Path $PRETRAIN_MARK)) {

    Log "DECISÃO: MODELO AINDA NÃO FOI PRÉ-TREINADO"
    Log "AÇÃO  : EXECUTAR PRÉ-TREINO (UMA ÚNICA VEZ)"

    # --------------------------------------------------------
    # ETAPA 2.1 — GERAR DADOS SINTÉTICOS
    # --------------------------------------------------------
    Run-Step `
        "SYNTHETIC PRETRAIN DATA (LS17 v4)" `
        @($PYTHON, "synthetic_pretrain_ls17_mega_v4.py") `
        $MEGA_DIR

    # --------------------------------------------------------
    # ETAPA 2.2 — TREINO COM PRÉ-TREINO
    # --------------------------------------------------------
    Run-Step `
        "TRAIN LS17 MEGA V4 (COM PRÉ-TREINO)" `
        @($PYTHON, "train\train_ls17_mega_v4.py", "--pretrain") `
        $MEGA_DIR

    New-Item -ItemType File -Path $PRETRAIN_MARK -Force | Out-Null
    Log "MARCADOR DE PRÉ-TREINO CRIADO: $PRETRAIN_MARK"

}
else {

    Log "DECISÃO: MODELO JÁ PRÉ-TREINADO"
    Log "AÇÃO  : PULAR PRÉ-TREINO (REGRA DE SEGURANÇA)"
}

# ------------------------------------------------------------
# ETAPA 3 — TREINO NORMAL (SEMPRE)
# ------------------------------------------------------------
Run-Step `
    "TRAIN LS17 MEGA V4 (TREINO NORMAL)" `
    @($PYTHON, "train\train_ls17_mega_v4.py") `
    $MEGA_DIR

# ------------------------------------------------------------
# ETAPA 4 — VALIDAÇÃO
# ------------------------------------------------------------
Run-Step `
    "VALIDATE LS17 MEGA V4" `
    @($PYTHON, "validate\validate_ls17_mega_v4.py") `
    $MEGA_DIR

# ------------------------------------------------------------
# FINALIZAÇÃO
# ------------------------------------------------------------
Log "PIPELINE LS17 MEGA-SENA V4 FINALIZADO COM SUCESSO"
Log "LOG SALVO EM: $LOG_FILE"
