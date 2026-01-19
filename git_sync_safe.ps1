# ============================================================
# git_sync_safe.ps1
# Pipeline seguro de sincronização Git (Dev -> Prod)
# Autor: FaixaBet (Corrigido por Agent)
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "     GIT SYNC GLOBAL - CORE & MODULES" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

Write-Host "Analisando alteracoes do projeto..." -ForegroundColor Cyan

# ------------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------------
$ROOT = Get-Location
$LOG_DIR = Join-Path $ROOT "logs"
$LOG_FILE = Join-Path $LOG_DIR "git_sync_log.csv"

# LISTA DE EXCLUSÃO (Negativa)
# Arquivos/Pastas que contêm estas strings serão IGNORADOS
# Bugfix: removemos "modelo_llm_max" global para permitir source code,
# e adicionamos especificamente "models" dentro dele.
$IGNORED_PATHS = @(
    "models/",                     # Pasta models na raiz (se houver)
    "modelo_llm_max/models/",      # PESADOS: Modelos binários (.keras, .h5, etc)
    "modelo_llm_max/dados/",       # PESADOS: Dados brutos/intermediários
    "modelo_llm_max/dados_m/",
    "modelo_llm_max/output/",
    ".env",                        # Segredos
    "logs/",                       # Logs
    "__pycache__",                 # Cache Python
    ".DS_Store",
    ".git/"                        # Próprio git
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
Write-Host "Executando git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain

if (-not $gitStatus) {
    Write-Host "Nenhuma alteracao detectada." -ForegroundColor Green
    exit 0
}

# Converte output do git status em lista de arquivos
$FILES_RAW = @(
    $gitStatus | ForEach-Object {
        # Formato: " M file.txt", "?? file.txt" -> Remove status (3 primeiros chars) e trim
        $_.Substring(3).Trim()
    }
)

# ------------------------------------------------------------
# FILTRA CAMINHOS IGNORADOS
# ------------------------------------------------------------
Write-Host "Filtrando arquivos ignorados..." -ForegroundColor Yellow

$FILES_TO_ADD = @(
    $FILES_RAW | Where-Object {
        $path = $_ -replace "\\", "/"  # Normaliza para / para comparar
        $keep = $true
        
        foreach ($ig in $IGNORED_PATHS) {
            # Se o caminho contiver o padrão ignorado
            if ($path -like "*$ig*") { 
                $keep = $false 
                # Write-Host "  [IGN] $path (pattern: $ig)" -ForegroundColor DarkGray
                break
            }
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
Write-Host "`nArquivos que serao versionados:" -ForegroundColor Green
$FILES_TO_ADD | ForEach-Object { Write-Host "  [+] $_" }

$confirm = Read-Host "`nDeseja realizar o COMMIT e PUSH destes arquivos? (s/n)"
if ($confirm -ne "s") {
    Write-Host "Operacao cancelada." -ForegroundColor Yellow
    exit 0
}

# ------------------------------------------------------------
# ADD SEGURO
# ------------------------------------------------------------
foreach ($file in $FILES_TO_ADD) {
    try {
        git add -- "$file"
        Write-Log $file "ADD_OK" "Stage sucesso"
    } catch {
        Write-Log $file "ADD_ERRO" $_.Exception.Message
        Write-Host "Erro ao adicionar $file" -ForegroundColor Red
        throw
    }
}

# ------------------------------------------------------------
# COMMIT
# ------------------------------------------------------------
$commitMsg = "sync: atualizacao modulos v9 (incluindo lotofacil) $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

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
Write-Host "Enviando para remoto..." -ForegroundColor Yellow
try {
    git push
    Write-Host "Push concluido com sucesso." -ForegroundColor Green
} catch {
    Write-Host "ERRO no push. Commit mantido localmente." -ForegroundColor Red
    throw
}

Write-Host "Pipeline Git Global finalizado com sucesso." -ForegroundColor Cyan
