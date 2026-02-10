$baseUrl = "http://127.0.0.1:5000"

function Test-Settings {
    Write-Host "`n[TEST] Settings Endpoints"
    $newKey = "test_key_" + [guid]::NewGuid().ToString()
    Write-Host "  > Setting Gemini API Key to: $newKey"

    try {
        $body = @{ gemini_api_key = $newKey } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/settings" -Method Post -Body $body -ContentType "application/json"
        Write-Host "  > POST Response: $($response.status)"
    }
    catch {
        Write-Host "  [FAIL] POST /api/settings error: $_"
        return
    }

    Write-Host "  > Retrieving Settings..."
    try {
        $data = Invoke-RestMethod -Uri "$baseUrl/api/settings" -Method Get
        if ($data.gemini_api_key -eq $newKey) {
            Write-Host "  [PASS] API Key persistence verified."
        }
        else {
            Write-Host "  [FAIL] API Key mismatch. Expected $newKey, got $($data.gemini_api_key)"
        }
    }
    catch {
        Write-Host "  [FAIL] GET /api/settings error: $_"
    }
}

function Test-Inventory {
    Write-Host "`n[TEST] Inventory Settings"
    $dayPack = 55
    $nightPack = 35
    Write-Host "  > Setting Diaper Packs: Day=$dayPack, Night=$nightPack"

    try {
        $body = @{ diaper_day_pack = $dayPack; diaper_night_pack = $nightPack } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/api/inventory/settings" -Method Post -Body $body -ContentType "application/json"
        Write-Host "  > POST Response: $($response.status)"
    }
    catch {
        Write-Host "  [FAIL] POST /api/inventory/settings error: $_"
        return
    }

    Write-Host "  > Verifying via GET /api/settings..."
    try {
        $data = Invoke-RestMethod -Uri "$baseUrl/api/settings" -Method Get
        $packs = $data.diaper_pack_sizes
        if ($packs.diaper_day -eq $dayPack -and $packs.diaper_night -eq $nightPack) {
            Write-Host "  [PASS] Diaper persistence verified."
        }
        else {
            Write-Host "  [FAIL] Pack size mismatch. Got $($packs | ConvertTo-Json -Compress)"
        }
    }
    catch {
        Write-Host "  [FAIL] Verification error: $_"
    }
}

function Test-GrowthPrediction {
    Write-Host "`n[TEST] Growth Prediction"
    try {
        $data = Invoke-RestMethod -Uri "$baseUrl/api/growth/predict" -Method Get
        if ($data.status -eq "success" -and $data.predictions) {
            Write-Host "  [PASS] Growth prediction data retrieved. Count: $($data.predictions.Count)"
        }
        else {
            Write-Host "  [WARN] Unexpected response: $($data | ConvertTo-Json -Depth 2)"
        }
    }
    catch {
        Write-Host "  [FAIL] /api/growth/predict error: $_"
    }
}

function Test-SleepAnalysis {
    Write-Host "`n[TEST] Sleep Analysis"
    try {
        $data = Invoke-RestMethod -Uri "$baseUrl/api/sleep/analysis" -Method Get
        if ($data.status -eq "success") {
            Write-Host "  [PASS] Sleep analysis retrieved."
            if ($data.analysis) {
                Write-Host "  > Nap: $($data.analysis.nap | ConvertTo-Json -Compress)"
                Write-Host "  > Night: $($data.analysis.night | ConvertTo-Json -Compress)"
                Write-Host "  > Prediction: $($data.analysis.prediction)"
            }
            else {
                Write-Host "  > No analysis data (might differ if no sleep logs exist)."
            }
        }
        else {
            Write-Host "  [FAIL] Sleep analysis failed: $($data | ConvertTo-Json -Depth 2)"
        }
    }
    catch {
        Write-Host "  [FAIL] /api/sleep/analysis error: $_"
    }
}

Test-Settings
Test-Inventory
Test-GrowthPrediction
Test-SleepAnalysis
