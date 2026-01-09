<#
===============================================================================
 Projeto      : FaixaBet V9
 Script       : git_sync.ps1
 Autor        : Carlos (FaixaBet)
 Versao       : 1.0.0
 Data         : 2026-01-09

 Descricao:
 ------------------------------------------------------------------------------
 Pipeline simples Dev -> Prod para o projeto FaixaBet V9.

 Fluxo:
 1. Verifica branch atual
 2. Mostra status e resumo das mudancas
 3. Confirma com o usuario
 4. Executa add / commit
 5. Faz pull --rebase
 6. Faz push para origin/main

 Uso:
 ------------------------------------------------------------------------------
 cd C:\Faixabet\V9
 powershell -ExecutionPolicy Bypass -File git_sync.ps1
===============================================================================
#>

# -------------------------------
# VALIDACOES INICIAIS
# -------------------------------
if (-not (Test-Path ".git")) {
    Write-Host "ERRO: Este diretorio nao eh um repositorio Git."
    exit 1
}

$branch = git branch --show-current
if ($branch -ne "main") {
    Write-Host "ERRO: Voce esta na branch '$branch'."
    Write-Host "Troque para 'main' antes de subir para producao."
    exit 1
}

Write-Host ""
Write-Host "Branch atual: main (PRODUCAO)"
Write-Host ""

# -------------------------------
# STATUS DO REPOSITORIO
# -------------------------------
git status

Write-Host ""
Write-Host "Resumo das mudancas (diff):"
Write-Host "---------------------------------------"
git diff --stat
Write-Host "---------------------------------------"
Write-Host ""

# -------------------------------
# CONFIRMACAO DO USUARIO
# -------------------------------
$confirm = Read-Host "Deseja versionar e subir essas alteracoes para PROD? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Operacao cancelada pelo usuario."
    exit 0
}

# -------------------------------
# COMMIT
# -------------------------------
$commitMsg = Read-Host "Digite a mensagem do commit"

if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    Write-Host "ERRO: Mensagem de commit nao pode ser vazia."
    exit 1
}

git add .

git commit -m "$commitMsg"

# -------------------------------
# SINCRONIZACAO COM REMOTO
# -------------------------------
Write-Host ""
Write-Host "Sincronizando com origin/main (rebase)..."
git pull --rebase origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERRO durante o rebase."
    Write-Host "Resolva os conflitos manualmente e depois execute:"
    Write-Host "  git rebase --continue"
    exit 1
}

# -------------------------------
# PUSH FINAL (PROD)
# -------------------------------
Write-Host ""
Write-Host "Enviando para producao (origin/main)..."
git push origin main

Write-Host ""
Write-Host "SUCESSO: Codigo versionado e enviado para PROD."
