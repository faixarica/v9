<#
===============================================================================
 Projeto      : FaixaBet V9
 Script       : setup_project_structure.ps1
 Autor        : Carlos (FaixaBet)
 Versao       : 1.1.0
 Data         : 2026-01-09

 Descricao:
 ------------------------------------------------------------------------------
 Script de bootstrap para criar e padronizar a estrutura oficial
 do projeto FaixaBet V9.

 - Cria pastas oficiais do projeto
 - Cria arquivos base (se nao existirem)
 - Nao sobrescreve nada
 - Seguro para rodar varias vezes
 - Serve como documentacao viva para novos devs

 Como usar:
 ------------------------------------------------------------------------------
 cd C:\Faixabet\V9
 powershell -ExecutionPolicy Bypass -File setup_project_structure.ps1
===============================================================================
#>

# -------------------------------
# CONFIGURACAO INICIAL
# -------------------------------
$ROOT = Get-Location
Write-Host "Inicializando estrutura do projeto FaixaBet V9 em: $ROOT"

# -------------------------------
# FUNCOES UTILITARIAS
# -------------------------------
function Ensure-Directory {
    param ([string]$Path)

    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "Criado diretorio: $Path"
    } else {
        Write-Host "Diretorio ja existe: $Path"
    }
}

function Ensure-File {
    param (
        [string]$Path,
        [string]$Content = ""
    )

    if (-not (Test-Path $Path)) {
        $Content | Out-File -FilePath $Path -Encoding UTF8
        Write-Host "Criado arquivo: $Path"
    } else {
        Write-Host "Arquivo ja existe: $Path"
    }
}

# -------------------------------
# ESTRUTURA DE DIRETORIOS
# -------------------------------
Ensure-Directory "$ROOT/app"
Ensure-Directory "$ROOT/services"
Ensure-Directory "$ROOT/admin"
Ensure-Directory "$ROOT/assets"
Ensure-Directory "$ROOT/mega"

# -------------------------------
# ARQUIVO PRINCIPAL STREAMLIT
# -------------------------------
Ensure-File "$ROOT/streamlit_app.py" @"
"""
FaixaBet V9 - Streamlit App

Arquivo principal de entrada da aplicacao.
Responsavel por inicializar a UI e integrar os modulos.
"""
"@

# -------------------------------
# ADMIN - SCRIPTS OPERACIONAIS
# -------------------------------
$adminFiles = @(
    "email_estatisticas_user.py",
    "email_notificar_user.py",
    "email_enviar_reset_manual.py",
    "notifica.py",
    "usuarios.py",
    "lotaria.py",
    "loteriamega.py",
    "reset_manual.py"
)

foreach ($file in $adminFiles) {
    Ensure-File "$ROOT/admin/$file" @"
"""
FaixaBet V9 - Script Administrativo
Arquivo: $file

Uso:
- Scripts internos e operacionais
- Nao expor diretamente ao usuario final
"""
"@
}

# -------------------------------
# FINALIZACAO
# -------------------------------
Write-Host ""
Write-Host "Estrutura do projeto FaixaBet V9 verificada/criada com sucesso."
Write-Host "Pronto para desenvolvimento, versionamento e deploy."
