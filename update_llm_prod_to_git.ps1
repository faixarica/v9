
# comand  exec.: powershell -File "C:\Faixabet\V8\update_llm_prod_to_git.ps1"

Write-Host "Iniciando atualização dos modelos..." -ForegroundColor Cyan

$DataAtual = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

cd "C:\Faixabet\V8"

git add "modelo_llm_max\models\prod"

git commit -m "Atualização automática dos modelos prod - $DataAtual"

git push origin main

Write-Host "✅ Concluído com sucesso!" -ForegroundColor Green
