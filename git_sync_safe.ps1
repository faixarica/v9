<#
===============================================================================
 Projeto      : FaixaBet V9
 Script       : git_sync_safe.ps1
 Autor        : Carlos (FaixaBet)
 Versao       : 2.0.0
 Data         : 2026-01-09

 Pipeline DEV → PROD com protecao total contra perda de codigo
===============================================================================
#>

# -------------------------------
# VALIDACOES
# -------------------------------
if (-not (Test-Path ".git")) {
    Write-Host "ERRO: Diretorio nao eh repositorio Git."
    exit 1
}

$branch = git branch --show-current
if ($branch -ne "main") {
    Write-Host "ERRO: Branch atual = $branch (use main)"
    exit 1
}

# -------------------------------
# BACKUP DE SEGURANCA
# -------------------------------
$backupDir = "..\_backup_git_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Write-Host "Criando backup em $backupDir"
Copy-Item . $backupDir -Recurse -Force

# -------------------------------
# PULL PRIMEIRO (REGRA DE OURO)
# -------------------------------
Write-Host "`nAtualizando com origin/main..."
git pull origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO no pull. Abortando."
    exit 1
}

# -------------------------------
# STATUS
# -------------------------------
git status
git diff --stat

$confirm = Read-Host "`nDeseja commitar e subir para PROD? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Cancelado."
    exit 0
}

# -------------------------------
# COMMIT CONTROLADO
# -------------------------------
$commitMsg = Read-Host "Mensagem do commit"
if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    Write-Host "Mensagem vazia."
    exit 1
}

# 🔒 ADD SELETIVO (NUNCA add .)
git add app admin services assets mega streamlit_app.py welcome.py

git commit -m "$commitMsg"

# -------------------------------
# PUSH
# -------------------------------
git push origin main

Write-Host "`nSUCESSO: Deploy seguro finalizado."
