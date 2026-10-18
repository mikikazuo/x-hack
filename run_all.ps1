# UTF-8 出力設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $scriptDir ".venv\Scripts\python.exe"

$modes = @(
    @{ Name = "KEIBA"; Arg = "keiba" },
    @{ Name = "FITNESS_JP"; Arg = "goutraining-jp" },
    @{ Name = "FITNESS_EN"; Arg = "goutraining-eng" },
    @{ Name = "RICE"; Arg = "rice" },
    @{ Name = "ANIPATH"; Arg = "anipath" }
)

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "X(Twitter) Bot 個別ウィンドウ一括起動スクリプト" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "5つのアカウントを独立したウィンドウで起動します..." -ForegroundColor Yellow
Write-Host ""

foreach ($m in $modes) {
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "title Bot [$($m.Name)] && `"$pythonPath`" main.py --mode $($m.Arg)" -WorkingDirectory $scriptDir
    Write-Host "起動: Bot [$($m.Name)] (モード: $($m.Arg))" -ForegroundColor Green
}

Write-Host ""
Write-Host "すべてのBotを別ウィンドウで起動しました。" -ForegroundColor Cyan
