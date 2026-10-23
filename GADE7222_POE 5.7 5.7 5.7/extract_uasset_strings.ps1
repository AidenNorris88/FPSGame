$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Files = @(
    "Content\AI\BP_EnemyGuard.uasset",
    "Content\Blueprints\BP_Player.uasset",
    "Content\Blueprints\BP_Projectile.uasset",
    "Content\Blueprints\Bp_HealthComponent.uasset",
    "Content\AI\BT_Enemy_Base.uasset"
)
$Keywords = @("spawn","projectile","player","fire","attack","damage","health","collision","class","mesh","overlap","hit")
$MinLen = 4
$MaxStrings = 200
$SpawnWindow = 512

function Get-AsciiStrings([byte[]]$Data, [int]$MinLen = 4) {
    $results = [System.Collections.Generic.List[string]]::new()
    $seen = @{}
    $sb = [System.Text.StringBuilder]::new()
    foreach ($b in $Data) {
        if ($b -ge 0x20 -and $b -le 0x7e) {
            [void]$sb.Append([char]$b)
        } else {
            if ($sb.Length -ge $MinLen) {
                $s = $sb.ToString()
                if (-not $seen.ContainsKey($s)) {
                    $seen[$s] = $true
                    $results.Add($s)
                }
            }
            [void]$sb.Clear()
        }
    }
    if ($sb.Length -ge $MinLen) {
        $s = $sb.ToString()
        if (-not $seen.ContainsKey($s)) { $results.Add($s) }
    }
    return $results
}

function Test-Keyword([string]$s) {
    $lower = $s.ToLowerInvariant()
    foreach ($kw in $Keywords) {
        if ($lower.Contains($kw)) { return $true }
    }
    return $false
}

function Find-SpawnProximity([byte[]]$Data) {
    $markers = @(
        [System.Text.Encoding]::ASCII.GetBytes("K2_SpawnActor"),
        [System.Text.Encoding]::ASCII.GetBytes("SpawnActor"),
        [System.Text.Encoding]::ASCII.GetBytes("BeginDeferredActorSpawnFromClass"),
        [System.Text.Encoding]::ASCII.GetBytes("FinishSpawningActor")
    )
    $hits = @()
    foreach ($marker in $markers) {
        $markerStr = [System.Text.Encoding]::ASCII.GetString($marker)
        for ($idx = 0; $idx -le $Data.Length - $marker.Length; $idx++) {
            $match = $true
            for ($j = 0; $j -lt $marker.Length; $j++) {
                if ($Data[$idx + $j] -ne $marker[$j]) { $match = $false; break }
            }
            if (-not $match) { continue }
            $lo = [Math]::Max(0, $idx - $SpawnWindow)
            $hi = [Math]::Min($Data.Length, $idx + $marker.Length + $SpawnWindow)
            $len = $hi - $lo
            $window = New-Object byte[] $len
            [Array]::Copy($Data, $lo, $window, 0, $len)
            $strings = Get-AsciiStrings $window 3
            $interesting = $strings | Where-Object {
                $_ -match "BP_Player|Player|Spawn|Class|Projectile"
            } | Select-Object -First 30
            $hits += [PSCustomObject]@{
                Marker = $markerStr
                Offset = $idx
                Nearby = $interesting
            }
        }
    }
    return $hits
}

foreach ($rel in $Files) {
    $path = Join-Path $ProjectRoot $rel
    Write-Output ("=" * 72)
    Write-Output "FILE: $rel"
    Write-Output ("=" * 72)
    if (-not (Test-Path $path)) {
        Write-Output "  [MISSING]"
        continue
    }
    $data = [System.IO.File]::ReadAllBytes($path)
    $all = Get-AsciiStrings $data $MinLen
    $filtered = $all | Where-Object { Test-Keyword $_ } | Select-Object -First $MaxStrings
    Write-Output "  Total ASCII strings (len>=$MinLen): $($all.Count)"
    Write-Output "  Filtered (keywords): $($filtered.Count) (showing up to $MaxStrings)"
    Write-Output ""
    $i = 0
    foreach ($s in $filtered) {
        $i++
        Write-Output ("  {0,4}. {1}" -f $i, $s)
    }
    Write-Output ""
    Write-Output "  --- Spawn API proximity (BP_Player / spawn class) ---"
    $spawnHits = Find-SpawnProximity $data
    if ($spawnHits.Count -eq 0) {
        Write-Output "  No K2_SpawnActor / SpawnActor markers found in this file."
    } else {
        foreach ($h in $spawnHits) {
            $hasBp = $false
            foreach ($n in $h.Nearby) { if ($n -like "*BP_Player*") { $hasBp = $true; break } }
            $flag = if ($hasBp) { " *** BP_Player nearby ***" } else { "" }
            Write-Output ("  @ offset {0}: {1}{2}" -f $h.Offset, $h.Marker, $flag)
            foreach ($n in ($h.Nearby | Select-Object -First 15)) {
                Write-Output "      -> $n"
            }
        }
    }
    $bpNear = $spawnHits | Where-Object { ($_.Nearby | Where-Object { $_ -like "*BP_Player*" }).Count -gt 0 }
    Write-Output ""
    if ($bpNear.Count -gt 0) {
        Write-Output "  CONCLUSION: BP_Player appears near spawn-related API in this file."
    } elseif (($spawnHits | Where-Object { $_.Marker -eq "K2_SpawnActor" }).Count -gt 0) {
        Write-Output "  CONCLUSION: K2_SpawnActor found but BP_Player not in nearby window."
    }
    Write-Output ""
}
