# --- SETTINGS ---
$target = "C:\Users\DanV\PFB\FBP_Copy\FBModules\FBOperations\FBPythonProject\fbmathengine\__FBMathEngine__"
$reports = "C:\Users\DanV\PFB\FBP_Copy\Reports"

Write-Host "`n=== Scanning $target ===`n"

# --- 1. Show empty files ---
$empty = Get-ChildItem -Path $target -File -ErrorAction SilentlyContinue | Where-Object { $_.Length -eq 0 }
if ($empty) {
    Write-Host "Empty files found:`n"
    $empty | Format-Table Name, Length
    $ans = Read-Host "Delete these empty files? (y/n)"
    if ($ans -eq 'y') { $empty | Remove-Item -Verbose }
} else {
    Write-Host "No empty files.`n"
}

# --- 2. Find duplicate stems ---
$dupes = Get-ChildItem -Path $target -File -ErrorAction SilentlyContinue |
    Group-Object BaseName | Where-Object { $_.Count -gt 1 }

if ($dupes) {
    Write-Host "`nPossible duplicates:`n"
    foreach ($d in $dupes) {
        $d.Group | Format-Table Name, Length
        $ans = Read-Host "Delete any of these? (type filename or press Enter to skip)"
        if ($ans) {
            $path = Join-Path $target $ans
            if (Test-Path $path) { Remove-Item $path -Verbose }
        }
    }
} else {
    Write-Host "No duplicate base names.`n"
}

# --- 3. Optional: clean old reports (>10 days) ---
if (Test-Path $reports) {
    Write-Host "`nChecking old reports in $reports`n"
    $old = Get-ChildItem -Path $reports -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-10) }
    if ($old) {
        $old | Format-Table Name, LastWriteTime
        $ans = Read-Host "Delete these old reports? (y/n)"
        if ($ans -eq 'y') { $old | Remove-Item -Verbose }
    } else {
        Write-Host "No reports older than 10 days.`n"
    }
} else {
    Write-Host "`nNo Reports folder found at $reports`n"
}

Write-Host "`nCleanup pass complete.`n"
