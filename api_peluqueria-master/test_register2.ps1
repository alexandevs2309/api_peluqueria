$body = @{
    fullName = "Alexander Test"
    email = "alexanderdelrosarioperez@gmail.com"
    businessName = "Barberia Alexander"
    planType = "trial"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://api-peluqueria-p25h.onrender.com/api/subscriptions/register/" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    $response | ConvertTo-Json -Depth 5
} catch {
    $_.ErrorDetails.Message
}
