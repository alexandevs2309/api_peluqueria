$body = @{
    fullName = "Alexander Test"
    email = "test@test.com"
    businessName = "Barberia Test"
    planType = "trial"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://api-peluqueria-p25h.onrender.com/api/subscriptions/register/" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$response | ConvertTo-Json
