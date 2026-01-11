# ============================================================
# git_sync_safe.ps1
# Pipeline seguro de sincronização Git (Dev → Prod)
# Autor: FaixaBet
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "Analisando alteracoes do projeto..." -ForegroundColor Cyan

# ------------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------------
$ROOT = Get-Location
$LOG_DIR = Join-Path $ROOT "logs"
$LOG_FILE = Join-Path $LOG_DIR "git_sync_log.csv"

$IGNORED_PATHS = @(
    "models",
    "models/",
    "modelo_llm_max",
    ".env",
    "logs/"
)

# ------------------------------------------------------------
# GARANTE DIRETÓRIO DE LOG
# ------------------------------------------------------------
if (!(Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR | Out-Null
}

# ------------------------------------------------------------
# FUNÇÃO DE LOG CSV
# ------------------------------------------------------------
function Write-Log {
    param (
        [string]$Arquivo,
        [string]$Status,
        [string]$Mensagem
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "$timestamp;$Arquivo;$Status;$Mensagem"

    if (!(Test-Path $LOG_FILE)) {
        "data_hora;arquivo;status;mensagem" | Out-File -FilePath $LOG_FILE -Encoding UTF8
    }

    $line | Out-File -FilePath $LOG_FILE -Append -Encoding UTF8
}

# ------------------------------------------------------------
# INICIALIZAÇÃO DEFENSIVA
# ------------------------------------------------------------
$FILES_TO_ADD = @()

# ------------------------------------------------------------
# COLETA ALTERAÇÕES DO GIT
# ------------------------------------------------------------
$gitStatus = git status --porcelain

if (-not $gitStatus) {
    Write-Host "Nenhuma alteracao detectada." -ForegroundColor Yellow
    exit 0
}

$FILES_TO_ADD = @(
    $gitStatus | ForEach-Object {
        $_.Substring(3).Trim()
    }
)

# ------------------------------------------------------------
# FILTRA CAMINHOS IGNORADOS
# ------------------------------------------------------------
$FILES_TO_ADD = @(
    $FILES_TO_ADD | Where-Object {
        $keep = $true
        foreach ($ig in $IGNORED_PATHS) {
            if ($_ -like "$ig*") { $keep = $false }
        }
        $keep
    }
)

# ------------------------------------------------------------
# VALIDA SE RESTOU ALGO
# ------------------------------------------------------------
if ($FILES_TO_ADD.Length -eq 0) {
    Write-Host "Apenas arquivos ignorados foram modificados. Nada a commitar." -ForegroundColor Yellow
    exit 0
}

# ------------------------------------------------------------
# EXIBE RESUMO
# ------------------------------------------------------------
Write-Host "Arquivos que serao versionados:" -ForegroundColor Green
$FILES_TO_ADD | ForEach-Object { Write-Host "  + $_" }

# ------------------------------------------------------------
# ADD SEGURO
# ------------------------------------------------------------
foreach ($file in $FILES_TO_ADD) {
    try {
        git add -- "$file"
        Write-Log $file "ADD_OK" "Arquivo adicionado com sucesso"
    } catch {
        Write-Log $file "ADD_ERRO" $_.Exception.Message
        throw
    }
}

# ------------------------------------------------------------
# COMMIT
# ------------------------------------------------------------
$commitMsg = "sync: atualizacao segura $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

try {
    git commit -m "$commitMsg" | Out-Null
    Write-Host "Commit realizado com sucesso." -ForegroundColor Green
} catch {
    Write-Host "Erro ao realizar commit." -ForegroundColor Red
    throw
}

# ------------------------------------------------------------
# PUSH
# ------------------------------------------------------------
try {
    git push
    Write-Host "Push concluido com sucesso." -ForegroundColor Green
} catch {
    Write-Host "ERRO no push. Commit mantido localmente." -ForegroundColor Red
    throw
}

Write-Host "Pipeline Git finalizado com sucesso." -ForegroundColor Cyan
