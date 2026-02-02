# generate-secrets.ps1 - Genera configuración segura para Windows PowerShell

Write-Host "🔐 Generando configuración segura..." -ForegroundColor Green

# Función para generar contraseña aleatoria
function Generate-RandomPassword {
    param([int]$Length = 25)
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $password = ""
    for ($i = 0; $i -lt $Length; $i++) {
        $password += $chars[(Get-Random -Maximum $chars.Length)]
    }
    return $password
}

# Generar SECRET_KEY de Django (sin caracteres problemáticos)
$secretKey = -join ((1..50) | ForEach {[char]((65..90) + (97..122) + (48..57) + (45,95) | Get-Random)})

# Generar contraseñas seguras
$dbPassword = Generate-RandomPassword -Length 25
$redisPassword = Generate-RandomPassword -Length 25

Write-Host "Generando secretos..." -ForegroundColor Yellow

# Crear .env desde template
if (Test-Path ".env.template") {
    Copy-Item ".env.template" ".env"
    
    # Reemplazar placeholders (con comillas para SECRET_KEY)
    (Get-Content ".env") -replace "CHANGE_ME_TO_RANDOM_SECRET_KEY", "`"$secretKey`"" -replace "CHANGE_DB_PASSWORD", $dbPassword -replace "CHANGE_REDIS_PASSWORD", $redisPassword | Set-Content ".env"
    
    Write-Host "✅ Archivo .env creado con secretos seguros" -ForegroundColor Green
} else {
    Write-Host "❌ No se encontró .env.template" -ForegroundColor Red
    exit 1
}

# Crear .env.prod desde template
if (Test-Path ".env.template") {
    Copy-Item ".env.template" ".env.prod"
    
    # Configuración específica de producción (con comillas para SECRET_KEY)
    (Get-Content ".env.prod") -replace "DEBUG=True", "DEBUG=False" -replace "ALLOWED_HOSTS=localhost,127.0.0.1", "ALLOWED_HOSTS=your-domain.com,api.your-domain.com" -replace "CHANGE_ME_TO_RANDOM_SECRET_KEY", "`"$secretKey`"" -replace "CHANGE_DB_PASSWORD", $dbPassword -replace "CHANGE_REDIS_PASSWORD", $redisPassword | Set-Content ".env.prod"
    
    Write-Host "✅ Archivo .env.prod creado para producción" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔑 CREDENCIALES GENERADAS:" -ForegroundColor Cyan
Write-Host "DB Password: $dbPassword" -ForegroundColor Yellow
Write-Host "Redis Password: $redisPassword" -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  IMPORTANTE: Guarda estas credenciales en un lugar seguro" -ForegroundColor Red
Write-Host "📝 Los archivos .env están listos para usar" -ForegroundColor Green