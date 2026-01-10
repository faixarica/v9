# ==========================================
# Git Sync Safe v2 - FaixaBet
# ==========================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = Get-Location
$LOG_FILE = "$ROOT\git_sync_log.csv"
$DATE = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Pastas FULL (commit tudo)
$FULL_DIRS = @(
    "app",
    "mega",
    "models",
    "assets"
)

# Pastas SELETIVAS (escolher arquivos)
$SELECTIVE_DIRS = @(
    ".",
    "admin"
)

# Criar log
if (!(Test-Path $LOG_FILE)) {
    "data_hora,arquivo,status,mensagem" | Out-File $LOG_FILE -Encoding UTF8
}

Write-Host ""
Write-Host "Analisando alteracoes do projeto..." -ForegroundColor Cyan

$FILES_TO_ADD = @()

# -------------------------------
# 1) Pastas FULL SNAPSHOT
# -------------------------------
foreach ($dir in $FULL_DIRS) {
    if (Test-Path $dir) {
        Write-Host "Snapshot completo: $dir" -ForegroundColor Yellow
        git add "$dir/"
        "$DATE,$dir,SUCESSO,snapshot completo" | Add-Content $LOG_FILE
    }
}

# -------------------------------
# 2) Pastas SELETIVAS
# -------------------------------
foreach ($dir in $SELECTIVE_DIRS) {

    git status --porcelain $dir | ForEach-Object {

        if ($_ -and $_.Length -gt 3) {
            $file = $_.Substring(3).Trim()
            if ($file) {
                $FILES_TO_ADD += $file
            }
        }
    }
}

$FILES_TO_ADD = $FILES_TO_ADD | Sort-Object | Get-Unique

if ($FILES_TO_ADD.Count -gt 0) {

    Write-Host ""
    Write-Host "Arquivos SELETIVOS detectados:" -ForegroundColor Yellow
    $FILES_TO_ADD | ForEach-Object {
        Write-Host " - $_"
    }

    $confirm = Read-Host "Adicionar esses arquivos seletivos? Digite YES"

    if ($confirm -ne "YES") {
        Write-Host "Abortado pelo usuario." -ForegroundColor Red
        exit
    }

    foreach ($file in $FILES_TO_ADD) {
        git add $file
        "$DATE,$file,SUCESSO,arquivo seletivo adicionado" | Add-Content $LOG_FILE
    }
}

# -------------------------------
# 3) Commit
# -------------------------------
$msg = Read-Host "Mensagem do commit (obrigatoria)"
if ([string]::IsNullOrWhiteSpace($msg)) {
    Write-Host "Mensagem vazia. Abortando." -ForegroundColor Red
    exit
}

git commit -m "$msg"

# -------------------------------
# 4) Pull + Push
# -------------------------------
git pull --rebase
git push

Write-Host ""
Write-Host "Git sincronizado com sucesso." -ForegroundColor Green
