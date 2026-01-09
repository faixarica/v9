# ======================================
# Git Push Seletivo - FaixaBet V9
# ======================================

Clear-Host
Write-Host "====================================="
Write-Host " Git Push Seletivo - FaixaBet V9"
Write-Host "====================================="

$paths = @(
    "app/services",
    "app/notificacoes",
    "app/assets",
    "mega"
)

Write-Host ""
Write-Host "Selecione o que deseja enviar para o Git:"
Write-Host ""

for ($i = 0; $i -lt $paths.Count; $i++) {
    Write-Host "[$($i+1)] $($paths[$i])"
}

Write-Host "[0] Cancelar"
Write-Host ""

$choice = Read-Host "Digite os numeros separados por virgula (ex: 1,3,4)"

if ($choice -eq "0" -or [string]::IsNullOrWhiteSpace($choice)) {
    Write-Host "Operacao cancelada."
    exit
}

$indexes = $choice -split "," | ForEach-Object { $_.Trim() }

foreach ($index in $indexes) {
    if ($index -match "^\d+$") {
        $i = [int]$index - 1
        if ($i -ge 0 -and $i -lt $paths.Count) {
            Write-Host "Adicionando $($paths[$i])"
            git add $paths[$i]
        }
        else {
            Write-Host "Indice invalido: $index"
        }
    }
}

$commitMsg = Read-Host "Mensagem do commit"

if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    $commitMsg = "Atualizacao seletiva"
}

git commit -m "$commitMsg"
git push

Write-Host ""
Write-Host "Push seletivo concluido com sucesso!"
