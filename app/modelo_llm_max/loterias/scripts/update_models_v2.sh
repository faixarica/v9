# ============================================================
#  update_models_v2.ps1 — Pipeline Completo fAIxaBet v2
#  Autor: Francisco F. (fAIxaBet)
#  Data: 2025-11-12
#  Descrição:
#     Gera datasets, re-treina LS14++ e LS15++, recria ensemble LS16,
#     e sincroniza modelos com o repositório Git.
# ============================================================

# comandos:
# simulação = powershell -ExecutionPolicy Bypass -File "update_models_v2.ps1" -WhatIf
# real 3h+- = powershell -ExecutionPolicy Bypass -File "update_models_v2.ps1"

# ========= CONFIGURAÇÃO INICIAL =========
$ErrorActionPreference = "Stop"
$basePath = "C:\Faixabet\V8\modelo_llm_max"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# ========= FUNÇÕES AUXILIARES =========
function Write-Log($msg, $color="White") {
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "[$time] $msg" -ForegroundColor $color
}

function Run-Step($desc, $cmd, $color="Cyan") {
    Write-Log ">>> $desc" $color
    try {
        & $cmd
        Write-Log "OK: $desc" "Green"
    } catch {
        Write-Log "ERRO: $desc -> $($_.Exception.Message)" "Red"
        exit 1
    }
    Write-Host ""
}

# ========= INÍCIO DO PROCESSO =========
Write-Host ""
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host "Iniciando pipeline completo - fAIxaBet v2" -ForegroundColor Green
Write-Host "Hora de início: $timestamp" -ForegroundColor DarkGray
Write-Host "=========================================" -ForegroundColor Yellow
Write-Host ""

Set-Location $basePath

# ========= 1) Atualiza dataset base =========
Run-Step "Atualizando dataset base (prepare_real_data_db.py)" {
    python "prepare_real_data_db.py"
}

# ========= 2) Treina LS14++ / LS15++ para Lotofácil =========
Run-Step "Treinando LS14++ / LS15++ (Lotofácil, recent/mid/global)" {
    python "train_llm_loteria_v2.py" --model both --loteria lotofacil --window 150
}

# ========= 3) Treina LS14++ / LS15++ para Mega-Sena =========
Run-Step "Treinando LS14++ / LS15++ (Mega-Sena, recent/mid/global)" {
    python "train_llm_loteria_v2.py" --model both --loteria mega --window 150
}

# ========= 4) Testes/ensemble LS16 (opcional, admin) =========
Run-Step "Rodando avaliação/ensemble (Lotofácil)" {
    python "ensemble_v2.py" --loteria lotofacil
}

Run-Step "Rodando avaliação/ensemble (Mega-Sena)" {
    python "ensemble_v2.py" --loteria mega
}

# ========= 5) Git =========
Run-Step "Commitando novos modelos no GitHub" {
    powershell -ExecutionPolicy Bypass -File "update_llm_prod_to_git.ps1"
}
