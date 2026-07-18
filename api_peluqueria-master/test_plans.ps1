$response = Invoke-RestMethod -Uri "https://api-peluqueria-p25h.onrender.com/api/subscriptions/plans/" `
    -Method GET `
    -ContentType "application/json"

$response | ConvertTo-Json -Depth 5
