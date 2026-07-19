# Script para eliminar console logs de archivos TypeScript

$sourceDir = "src\app"
$files = Get-ChildItem -Path $sourceDir -Filter "*.ts" -Recurse

$count = 0
foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    
    # Eliminar console.log, console.warn, console.error, console.info, console.debug
    $content = $content -replace "console\.(log|warn|error|info|debug)\([^)]*\);?\s*", ""
    
    # Eliminar líneas vacías múltiples
    $content = $content -replace "(\r?\n){3,}", "`r`n`r`n"
    
    if ($content -ne $originalContent) {
        Set-Content -Path $file.FullName -Value $content -NoNewline
        $count++
        Write-Host "Limpiado: $($file.FullName)"
    }
}

Write-Host "`nTotal archivos modificados: $count"
