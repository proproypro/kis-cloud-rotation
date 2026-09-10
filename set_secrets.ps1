# .env의 KIS 시크릿을 GitHub Actions Secrets로 등록 (값은 로컬→GitHub로만 흐름)
$envPath = "C:\Users\booyo\Downloads\kis-trading\.env"
if (-not (Test-Path $envPath)) { Write-Error ".env 없음: $envPath"; exit 1 }

$vals = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        $vals[$matches[1]] = $matches[2].Trim()
    }
}
foreach ($k in "KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO") {
    if ($vals[$k]) {
        $vals[$k] | gh secret set $k
        Write-Output "  $k 등록 완료"
    } else {
        Write-Output "  [경고] $k 를 .env에서 못 찾음"
    }
}
Write-Output "시크릿 등록 끝. (gh secret list 로 확인 가능)"
