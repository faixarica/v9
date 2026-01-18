# ============================================================
# run_megasena_pipeline.ps1
# Pipeline Auto-Adaptavel Mega-Sena — FaixaBet
# STRICT / FLEX + INVENTARIO + ROLLBACK
# PowerShell 5.1 SAFE
# ============================================================

$ErrorActionPreference = "Stop"

# ---------------- CONFIG ----------------
$BASE_DIR = "C:\Faixabet\V9"
$MEGA_DIR = "$BASE_DIR\modelo_llm_max\loterias\megasena"
$PYTHON   = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

# SETUP ENV ARGS FOR PYTHON "paths.py"
$env:FAIXABET_MODELS_DIR = "$BASE_DIR\modelo_llm_max\models"

$LOG_DIR = "$BASE_DIR\logs"
if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null }
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE = "$LOG_DIR\megasena_pipeline_$TIMESTAMP.log"

# ---------------- MODE ----------------
$MODE = "flex"   # strict | flex

# ---------------- MODELO ----------------
$MODEL_DIR     = "$env:FAIXABET_MODELS_DIR\megasena"
$MODEL_CURRENT = "$MODEL_DIR\ls17_megasena_v4.keras"
$MODEL_BACKUP  = "$MODEL_DIR\ls17_megasena_v4.prev.keras"

if (-not (Test-Path $MODEL_DIR)) { New-Item -ItemType Directory -Force -Path $MODEL_DIR | Out-Null }

# ============================================================
# LOG
# ============================================================
function Log {
    param ([string]$Msg)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
    Write-Host $line -ForegroundColor Cyan
    Add-Content -Path $LOG_FILE -Value $line
}

function Log-Error {
    param ([string]$Msg)
    $line = "[{0}] [ERROR] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
    Write-Host $line -ForegroundColor Red
    Add-Content -Path $LOG_FILE -Value $line
}

function Log-Warn {
    param ([string]$Msg)
    $line = "[{0}] [WARN] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
    Write-Host $line -ForegroundColor Yellow
    Add-Content -Path $LOG_FILE -Value $line
}

# ============================================================
# INPUT HELPER
# ============================================================
function Ask-User {
    param (
        [string]$Question,
        [string[]]$Options = @("s", "n"),
        [string]$Default = "s"
    )
    $validQuery = $Options -join "/"
    $inputStr = Read-Host "$Question ($validQuery) [Default: $Default]"
    if ([string]::IsNullOrWhiteSpace($inputStr)) { return $Default }
    if ($inputStr -in $Options) { return $inputStr }
    return $inputStr 
}

function Ask-YesNo {
    param ([string]$Question, [bool]$Default=$true)
    $defStr = if ($Default) { "s" } else { "n" }
    $ans = Ask-User $Question @("s", "n") $defStr
    return $ans -eq "s"
}

# ============================================================
# INVENTARIO
# ============================================================
function Get-LatestScript {
    param ([string]$Pattern)
    $files = Get-ChildItem -Path $MEGA_DIR -Recurse -Filter $Pattern -File -ErrorAction SilentlyContinue
    if (-not $files) { return $null }
    return $files | Sort-Object {
        if ($_.Name -match "vNext") { 0 }
        elseif ($_.Name -match "v5") { 1 }
        elseif ($_.Name -match "v4") { 2 }
        else { 9 }
    } | Select-Object -First 1
}

# ============================================================
# RUN STEP
# ============================================================
function Run-Step {
    param (
        [string]$Name,
        [string]$ScriptPath,
        [bool]$PassMode = $false
    )

    if (-not $ScriptPath) {
        Log-Warn ("{0} - SCRIPT NAO ENCONTRADO - SKIP" -f $Name)
        return "SKIP"
    }

    Log ("ETAPA: {0}" -f $Name)
    Log ("SCRIPT: {0}" -f $ScriptPath)

    $cmdArgs = @($ScriptPath)
    if ($PassMode) {
        $cmdArgs += "--mode"
        $cmdArgs += $MODE
    }
   
    Push-Location $MEGA_DIR
    
    $proc = Start-Process -FilePath $PYTHON -ArgumentList $cmdArgs -NoNewWindow -PassThru -Wait
    $exitCode = $proc.ExitCode
    
    Pop-Location

    Log ("EXIT CODE [{0}]: {1}" -f $Name, $exitCode)

    switch ($exitCode) {
        0  { return "OK" }
        10 { return "WARN" }
        20 { return "BLOCK" }
        30 { return "RULE" }
        1  { return "FATAL" }
        default {
            Log-Error ("ERRO DESCONHECIDO ({0})" -f $exitCode)
            return "FATAL"
        }
    }
}

# ============================================================
# MAIN PIPELINE
# ============================================================

Log "=================================================="
Log "PIPELINE MEGA-SENA - AUTO-ADAPTAVEL V2"
Log ("Modo   : {0}" -f $MODE)
Log "=================================================="

# 1. SETUP & CHECK
$SCRIPT_VALIDATE  = Get-LatestScript "validate_ms17*.py"
$SCRIPT_PREPARE   = Get-LatestScript "prepare_ms17*.py"
$SCRIPT_SYNTHETIC = Get-LatestScript "synthetic_ms17*.py"
$SCRIPT_SAMPLER   = Get-LatestScript "sampler_ms17*.py"
$SCRIPT_TRAIN     = Get-LatestScript "train_ls17*.py"
# New Evaluation Script - Explicitly finding evaluate_ms17_v4.py or matching pattern
$SCRIPT_EVALUATE  = Get-LatestScript "evaluate_ms17*.py" 

# REQUIREMENT CHECK
$fileRows = "$MEGA_DIR\prepare_real\dados\rows_60bin.npy"
if (-not (Test-Path $fileRows)) {
    Log-Error "ARQUIVO CRITICO AUSENTE: rows_60bin.npy"
    Log-Error "Local esperado: $fileRows"
    $ans = Ask-YesNo "Deseja tentar continuar mesmo assim (pode falhar)?" $false
    if (-not $ans) { exit 1 }
}

# 2. VALIDATE
$resValidate = "SKIP"
if ($SCRIPT_VALIDATE) {
    Log "--- VALIDACAO ---"
    $resValidate = Run-Step "VALIDATE" $SCRIPT_VALIDATE.FullName -PassMode $true
    
    if ($resValidate -eq "BLOCK") { 
        Log-Warn "Validacao indicou BLOCK (provavelmente dados ausentes)."
        $fix = Ask-YesNo "Deseja rodar PREPARE para corrigir?" $true
        if ($fix) {
            # Force Prepare
            $resPrepare = Run-Step "PREPARE" $SCRIPT_PREPARE.FullName -PassMode $false
            if ($resPrepare -eq "OK") {
                 # Re-Validate
                 Log "Re-validando apos Preparacao..."
                 $resValidate = Run-Step "VALIDATE" $SCRIPT_VALIDATE.FullName -PassMode $true
            } else {
                 Log-Error "Prep falhou. Nao e possivel corrigir validacao."
                 exit 1
            }
        } else {
             Log-Error "Usuario optou por nao corrigir. Abortando."
             exit 1
        }
    }
    elseif ($resValidate -eq "FATAL") {
        Log-Error "Erro Fatal na Validacao."
        exit 1
    }
}

# 3. PREPARE
if ($resValidate -eq "OK" -and (-not $resPrepare)) {
     $ask = Ask-YesNo "Validacao OK. Deseja rodar PREPARE novamente (Regerar dados)?" $false
     if ($ask) {
         $resPrepare = Run-Step "PREPARE" $SCRIPT_PREPARE.FullName -PassMode $false 
     } else {
         $resPrepare = "SKIP"
     }
}

# 4. SYNTHETIC
$resSynthetic = "SKIP"
if ($resValidate -in @("OK", "WARN")) {
    $askSynth = Ask-YesNo "Deseja rodar Geracao SINTECTICA?" $false
    if ($askSynth) {
        $resSynthetic = Run-Step "SYNTHETIC" $SCRIPT_SYNTHETIC.FullName -PassMode $false
    }
}

# 5. TRAIN (Reordered to be before EVAL/SAMPLER for logical flow)
$resTrain = "SKIP"
$askTrain = Ask-YesNo "Deseja rodar TREINO (Pode demorar)?" $true
if ($askTrain) {
     # Backup
     if (Test-Path $MODEL_CURRENT) {
        Copy-Item $MODEL_CURRENT $MODEL_BACKUP -Force
        Log "Backup criado: $MODEL_BACKUP"
     }

     $resTrain = Run-Step "TRAIN" $SCRIPT_TRAIN.FullName -PassMode $false

     if ($resTrain -in @("OK","WARN")) {
        Log "Treino OK. Modelo novo ativo."
        if (Test-Path $MODEL_BACKUP) { Remove-Item $MODEL_BACKUP -Force }
     } else {
        Log-Warn "Falha ou Rollback necessario no Treino."
        $rb = Ask-YesNo "Deseja realizar ROLLBACK para o modelo anterior?" $true
        if ($rb) {
            if (Test-Path $MODEL_BACKUP) {
                Copy-Item $MODEL_BACKUP $MODEL_CURRENT -Force
                Log "ROLLBACK EXECUTADO COM SUCESSO."
                $resTrain = "ROLLED_BACK"
            } else {
                Log-Error "Backup nao encontrado! Nao e possivel fazer Rollback."
            }
        }
     }
}

# 6. EVALUATE (New Step)
$resEvaluate = "SKIP"
if ($SCRIPT_EVALUATE -and ($resTrain -in @("OK", "WARN", "SKIP"))) {
    # If we trained, we definitely want to evaluate. If we skipped train, we might still want to evaluate current model.
    $askEval = Ask-YesNo "Deseja rodar AVALIACAO (Backtest)?" $true
    if ($askEval) {
         if (-not (Test-Path $MODEL_CURRENT)) {
              Log-Warn "Modelo nao encontrado para avaliacao."
         } else {
              $resEvaluate = Run-Step "EVALUATE" $SCRIPT_EVALUATE.FullName -PassMode $false
         }
    }
}

# 7. EXPORT (Production Artifact)
$SCRIPT_EXPORT = Get-LatestScript "export_ms17_inference.py"
$resExport = "SKIP"

if ($SCRIPT_EXPORT) {
    # Default to Yes if we trained or evaluated, or if artifact is missing
    $rankFile = "$env:FAIXABET_MODELS_DIR\megasena\ms17_v4_rank.npy"
    $needExport = $true
    if (-not (Test-Path $rankFile)) { $needExport = $true }
    elseif ($resTrain -eq "OK") { $needExport = $true }
    
    $askExport = Ask-YesNo "Deseja rodar EXPORTACAO (Gera artefato leve para Prod)?" $needExport
    if ($askExport) {
         if (-not (Test-Path $MODEL_CURRENT)) {
              Log-Warn "Modelo nao encontrado para exportacao."
         } else {
              $resExport = Run-Step "EXPORT" $SCRIPT_EXPORT.FullName -PassMode $false
         }
    }
}

# 7. SAMPLER
$resSampler = "SKIP"
# Only ask Sampler if Evaluation wasn't catastrophic (logic can be added later) or if user wants predictions
$askSampler = Ask-YesNo "Deseja rodar SAMPLER (Gerar palpites para HOJE)?" $true
if ($askSampler) {
     if (-not (Test-Path $MODEL_CURRENT)) {
          Log-Warn "Modelo nao encontrado ($MODEL_CURRENT). Necessario rodar TREINO primeiro."
          $resSampler = "SKIP"
     } else {
          $resSampler = Run-Step "SAMPLER" $SCRIPT_SAMPLER.FullName -PassMode $false
     }
}

Log "================ RESUMO FINAL ================"
Log ("VALIDATE  : {0}" -f $resValidate)
Log ("PREPARE   : {0}" -f $resPrepare)
Log ("SYNTHETIC : {0}" -f $resSynthetic)
Log ("TRAIN     : {0}" -f $resTrain)
Log ("EVALUATE  : {0}" -f $resEvaluate)
Log ("SAMPLER   : {0}" -f $resSampler)
Log "=============================================="
