# --- Root folders ---
$root    = "C:\Users\DanV\PFB\FBP_Copy\FBModules\FBOperations\FBPythonProject"
$reports = "C:\Users\DanV\PFB\FBP_Copy\Reports"

# --- Exclusions (won’t touch these trees) ---
$excludeDirs = @(".venv",".git",".idea",".vscode","__pycache__",".pytest_cache",".mypy_cache",".vs","node_modules")

Write-Host "`n=== Deep scan of $root ===`n"

# Helper: recursive file listing with exclusions
function Get-Files {
  Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
      $p = $_.FullName.ToLower()
      -not ($excludeDirs | ForEach-Object { $p -like "*\$_\*" })
    }
}

# 1) Empty files
$empty = Get-Files | Where-Object { $_.Length -eq 0 }
if ($empty) {
  Write-Host "Empty files:" -ForegroundColor Yellow
  $empty | Select-Object FullName, Length | Format-Table
  if ((Read-Host "Delete all empty files? (y/n)") -eq 'y') { $empty | Remove-Item -Verbose }
} else { Write-Host "No empty files.`n" }

# 2) Obvious junk (temp/backup)
$junkPatterns = @("*.tmp","*.bak","*~","*.orig","Thumbs.db",".DS_Store")
$junk = foreach ($pat in $junkPatterns) { Get-Files | Where-Object { $_.Name -like $pat } }
$junk = $junk | Sort-Object FullName -Unique
if ($junk) {
  Write-Host "`nJunk candidates:" -ForegroundColor Yellow
  $junk | Select-Object FullName, Length | Format-Table
  if ((Read-Host "Delete all junk candidates? (y/n)") -eq 'y') { $junk | Remove-Item -Verbose -Force }
} else { Write-Host "No junk candidates.`n" }

# 3) Python caches/bytecode
$pycacheDirs = Get-ChildItem -Path $root -Recurse -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -eq "__pycache__" -and -not ($excludeDirs -contains $_.Name) }
$pyc = Get-Files | Where-Object { $_.Extension -in ".pyc",".pyo" }

if ($pycacheDirs -or $pyc) {
  Write-Host "`nPython cache/bytecode:" -ForegroundColor Yellow
  $pyc | Select-Object FullName, Length | Format-Table
  $pycacheDirs | Select-Object FullName | Format-Table
  if ((Read-Host "Remove __pycache__ folders and *.pyc/*.pyo? (y/n)") -eq 'y') {
    $pyc | Remove-Item -Verbose -Force
    $pycacheDirs | Remove-Item -Recurse -Verbose -Force
  }
} else { Write-Host "No Python cache/bytecode found.`n" }

# 4) True duplicates by content (SHA256)
Write-Host "`nCalculating file hashes for duplicate detection (SHA256)..." -ForegroundColor Cyan
$allFiles = Get-Files
$hashed = $allFiles | ForEach-Object {
  try {
    $h = Get-FileHash -Algorithm SHA256 -Path $_.FullName -ErrorAction Stop
    [PSCustomObject]@{ FullName = $_.FullName; Length = $_.Length; LastWriteTime = $_.LastWriteTime; Hash = $h.Hash }
  } catch { $null }
}
$dupeGroups = $hashed | Group-Object Hash | Where-Object { $_.Count -gt 1 }

if ($dupeGroups) {
  Write-Host "`nDuplicate content groups (same hash):" -ForegroundColor Yellow
  foreach ($g in $dupeGroups) {
    Write-Host "`n--- DUPLICATE SET ---"
    $g.Group | Sort-Object LastWriteTime -Descending | Format-Table FullName, Length, LastWriteTime
    $keep = ($g.Group | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
    Write-Host "Will keep newest by default:`n$keep"

    $ans = Read-Host "Delete ALL other copies in this set? (y/n)"
    if ($ans -eq 'y') {
      $g.Group | Where-Object { $_.FullName -ne $keep } | ForEach-Object {
        Remove-Item $_.FullName -Verbose -Force
      }
    }
  }
} else {
  Write-Host "No content-duplicates found.`n"
}

# 5) Reports (older than 10 days)
if (Test-Path $reports) {
  $old = Get-ChildItem -Path $reports -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-10) }
  if ($old) {
    Write-Host ("`nOld reports in {0}:" -f $reports) -ForegroundColor Yellow
    $old | Select-Object Name, LastWriteTime | Format-Table
    if ((Read-Host "Delete these old reports? (y/n)") -eq 'y') { $old | Remove-Item -Verbose }
  } else { Write-Host "`nNo reports older than 10 days." }
} else {
  Write-Host "`nReports folder not found at: $reports"
}

Write-Host "`nDeep cleanup pass complete.`n"