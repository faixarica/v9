# ============================================================
# update_v9.ps1
# Atualização TOTAL segura do repositório faixarica/v9
# ============================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------------
$PROJECT_DIR = "C:\Faixabet\V9"
$BRANCH = "main"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🚀 UPDATE TOTAL - FAIXABET V9" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# ------------------------------------------------------------
# VERIFICA SE É REPO GIT
# ------------------------------------------------------------
Set-Location $PROJECT_DIR

if (!(Test-Path ".git")) {
    Write-Error "❌ Esta pasta não é um repositório Git."
}

# ------------------------------------------------------------
# STATUS ATUAL
# ------------------------------------------------------------
Write-Host "`n📌 Status atual:" -ForegroundColor Yellow
git status

# ------------------------------------------------------------
# GARANTIR BRANCH
# ------------------------------------------------------------
git checkout $BRANCH

# ------------------------------------------------------------
# LIMPEZA SEGURA (NÃO REMOVE IGNORE)
# ------------------------------------------------------------
Write-Host "`n🧹 Limpando arquivos temporários (seguro)..." -ForegroundColor Yellow
git clean -fd -e .env -e modelo_llm_max/models

# ------------------------------------------------------------
# PULL FORÇADO (SEM REBASE)
# ------------------------------------------------------------
Write-Host "`n⬇️ Atualizando repositório remoto..." -ForegroundColor Yellow
git fetch origin
git reset --hard origin/$BRANCH

# ------------------------------------------------------------
# DEPENDÊNCIAS (opcional)
# ------------------------------------------------------------
if (Test-Path "requirements.txt") {
    Write-Host "`n📦 Atualizando dependências..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
}

# ------------------------------------------------------------
# FINAL
# ------------------------------------------------------------
Write-Host "`n✅ UPDATE TOTAL FINALIZADO COM SUCESSO" -ForegroundColor Green
Write-Host "Branch: $BRANCH"
Write-Host "Diretório: $PROJECT_DIR"
