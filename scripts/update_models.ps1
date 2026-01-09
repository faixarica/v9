# ============================================================
# update_models.ps1
# Atualização TOTAL segura do repositório faixarica/models
# ============================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------------
$PROJECT_DIR = "C:\Faixabet\models"
$BRANCH = "main"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🧠 UPDATE TOTAL - FAIXABET MODELS (PRIVADO)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Set-Location $PROJECT_DIR

# ------------------------------------------------------------
# VERIFICA SE É REPO GIT
# ------------------------------------------------------------
if (!(Test-Path ".git")) {
    Write-Error "❌ Pasta models não é um repositório Git."
}

# ------------------------------------------------------------
# STATUS
# ------------------------------------------------------------
Write-Host "`n📌 Status atual:" -ForegroundColor Yellow
git status

# ------------------------------------------------------------
# GARANTIR BRANCH
# ------------------------------------------------------------
git checkout $BRANCH

# ------------------------------------------------------------
# LIMPEZA SEGURA (NÃO REMOVE MODELOS VERSIONADOS)
# ------------------------------------------------------------
Write-Host "`n🧹 Limpando cache e lixo..." -ForegroundColor Yellow
git clean -fd -e raw -e tmp

# ------------------------------------------------------------
# UPDATE FORÇADO
# ------------------------------------------------------------
Write-Host "`n⬇️ Sincronizando com GitHub (privado)..." -ForegroundColor Yellow
git fetch origin
git reset --hard origin/$BRANCH

# ------------------------------------------------------------
# FINAL
# ------------------------------------------------------------
Write-Host "`n✅ MODELS ATUALIZADO COM SUCESSO" -ForegroundColor Green
Write-Host "Branch: $BRANCH"
Write-Host "Diretório: $PROJECT_DIR"
