# PowerShell script to copy start app files
$source = "start-from-code-9c314cf4-main\src"
$dest = "webapp-react\src\apps\start\src"

Write-Host "Copying files from $source to $dest..."

if (-not (Test-Path $source)) {
    Write-Host "ERROR: Source directory not found: $source"
    exit 1
}

# Create destination directory if it doesn't exist
if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Write-Host "Created destination directory: $dest"
}

# Copy all files recursively
Get-ChildItem -Path $source -Recurse -File | ForEach-Object {
    $relativePath = $_.FullName.Substring((Resolve-Path $source).Path.Length + 1)
    $destPath = Join-Path $dest $relativePath
    $destDir = Split-Path $destPath -Parent
    
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    }
    
    Copy-Item $_.FullName -Destination $destPath -Force
}

Write-Host "Copy complete. Verifying..."

# Verify key files
$keyFiles = @(
    "pages\Index.tsx",
    "pages\Devices.tsx",
    "components\ProtectedRoute.tsx"
)

foreach ($file in $keyFiles) {
    $filePath = Join-Path $dest $file
    if (Test-Path $filePath) {
        Write-Host "✓ $file exists"
    } else {
        Write-Host "✗ $file MISSING"
    }
}

Write-Host "Done!"

