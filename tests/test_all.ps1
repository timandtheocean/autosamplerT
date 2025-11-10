# test_all.ps1 - PowerShell test script for AutosamplerT
# Comprehensive regression test suite
#
# Usage:
#   .\test_all.ps1                    # Run all tests
#   .\test_all.ps1 -Quick             # Run quick tests only
#   .\test_all.ps1 -Group basic       # Run specific test group

param(
    [switch]$Quick,
    [ValidateSet("basic", "velocity", "roundrobin", "combined", "audio", "metadata", "all")]
    [string]$Group = "all"
)

$ErrorActionPreference = "Continue"
$script:TestResults = @()
$script:TotalTests = 0
$script:PassedTests = 0
$script:FailedTests = 0
$script:StartTime = Get-Date

function Write-TestHeader {
    param([string]$Message)
    Write-Host "`n$('='*60)" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "$('='*60)" -ForegroundColor Cyan
}

function Write-TestResult {
    param(
        [string]$Name,
        [string]$Group,
        [bool]$Passed,
        [double]$Duration,
        [string]$ErrorMsg = ""
    )
    
    $script:TotalTests++
    if ($Passed) {
        $script:PassedTests++
        Write-Host "✓ PASSED" -ForegroundColor Green -NoNewline
        Write-Host " ($([math]::Round($Duration, 1))s)"
    } else {
        $script:FailedTests++
        Write-Host "✗ FAILED" -ForegroundColor Red -NoNewline
        Write-Host " ($([math]::Round($Duration, 1))s)"
        if ($ErrorMsg) {
            Write-Host "  Error: $ErrorMsg" -ForegroundColor Red
        }
    }
    
    $script:TestResults += [PSCustomObject]@{
        Name = $Name
        Group = $Group
        Passed = $Passed
        Duration = $Duration
        Error = $ErrorMsg
    }
}

function Invoke-Test {
    param(
        [string]$Name,
        [string]$Group,
        [string[]]$Arguments,
        [int]$ExpectedSamples = -1
    )
    
    Write-Host "`n$('='*60)" -ForegroundColor Yellow
    Write-Host "Test: $Name" -ForegroundColor Yellow
    Write-Host "Group: $Group" -ForegroundColor Yellow
    Write-Host "$('='*60)" -ForegroundColor Yellow
    
    $cmd = "python autosamplerT.py $($Arguments -join ' ')"
    Write-Host "Command: $cmd" -ForegroundColor Gray
    
    $testStart = Get-Date
    try {
        $output = & python autosamplerT.py @Arguments 2>&1
        $exitCode = $LASTEXITCODE
        $duration = (Get-Date) - $testStart
        $durationSec = $duration.TotalSeconds
        
        # Display output
        $output | ForEach-Object { Write-Host $_ }
        
        $passed = $exitCode -eq 0
        $errorMsg = ""
        
        # Verify sample count if specified
        if ($passed -and $ExpectedSamples -gt 0) {
            $nameIdx = $Arguments.IndexOf("--multisample_name")
            if ($nameIdx -ge 0 -and $nameIdx + 1 -lt $Arguments.Count) {
                $sampleName = $Arguments[$nameIdx + 1]
                $sampleDir = Join-Path "output" $sampleName "samples"
                
                if (Test-Path $sampleDir) {
                    $wavCount = (Get-ChildItem $sampleDir -Filter "*.wav").Count
                    if ($wavCount -ne $ExpectedSamples) {
                        $passed = $false
                        $errorMsg = "Expected $ExpectedSamples samples, found $wavCount"
                    } else {
                        $errorMsg = "Created $wavCount samples as expected"
                    }
                } else {
                    $passed = $false
                    $errorMsg = "Sample directory not found: $sampleDir"
                }
            }
        }
        
        Write-TestResult -Name $Name -Group $Group -Passed $passed -Duration $durationSec -ErrorMsg $errorMsg
        return $passed
        
    } catch {
        $duration = (Get-Date) - $testStart
        $durationSec = $duration.TotalSeconds
        Write-TestResult -Name $Name -Group $Group -Passed $false -Duration $durationSec -ErrorMsg $_.Exception.Message
        return $false
    }
}

# Base arguments for all tests
$baseArgs = @(
    "--hold_time", "1.0",
    "--release_time", "0.5",
    "--pause_time", "0.5"
)

# Group: Basic Sampling Tests
if ($Group -eq "all" -or $Group -eq "basic") {
    Write-TestHeader "GROUP: Basic Sampling"
    
    Invoke-Test -Name "Single note C4 (note name)" -Group "basic" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--multisample_name", "test_single_C4_cli")) `
        -ExpectedSamples 1
    
    Invoke-Test -Name "Single note 60 (MIDI number)" -Group "basic" `
        -Arguments ($baseArgs + @("--note_range_start", "60", "--note_range_end", "60", "--note_range_interval", "1", "--multisample_name", "test_single_60_cli")) `
        -ExpectedSamples 1
    
    Invoke-Test -Name "Four notes C4-C5 octave (note names)" -Group "basic" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C5", "--note_range_interval", "12", "--multisample_name", "test_four_octave_cli_names")) `
        -ExpectedSamples 2
    
    Invoke-Test -Name "Four notes 48-72 (MIDI numbers)" -Group "basic" `
        -Arguments ($baseArgs + @("--note_range_start", "48", "--note_range_end", "72", "--note_range_interval", "12", "--multisample_name", "test_four_octave_cli_midi")) `
        -ExpectedSamples 3
}

# Group: Velocity Layer Tests
if ($Group -eq "all" -or $Group -eq "velocity") {
    Write-TestHeader "GROUP: Velocity Layers"
    
    Invoke-Test -Name "Velocity layers: 4 layers (default auto)" -Group "velocity" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--velocity_layers", "4", "--multisample_name", "test_vel_auto_default")) `
        -ExpectedSamples 4
    
    Invoke-Test -Name "Velocity layers: 4 layers with minimum 45" -Group "velocity" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--velocity_layers", "4", "--velocity_minimum", "45", "--multisample_name", "test_vel_auto_min45")) `
        -ExpectedSamples 4
    
    Invoke-Test -Name "Velocity layers: 3 layers custom splits" -Group "velocity" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--velocity_layers", "3", "--velocity_layers_split", "50,90", "--multisample_name", "test_vel_custom_splits")) `
        -ExpectedSamples 3
    
    Invoke-Test -Name "Velocity layers: 1 layer (velocity 100)" -Group "velocity" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--velocity_layers", "1", "--velocity_minimum", "100", "--multisample_name", "test_vel_single")) `
        -ExpectedSamples 1
    
    Invoke-Test -Name "Velocity layers: 3 layers × 4 notes" -Group "velocity" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C5", "--note_range_interval", "5", "--velocity_layers", "3", "--multisample_name", "test_vel_noterange")) `
        -ExpectedSamples 9
}

# Group: Round-Robin Tests
if ($Group -eq "all" -or $Group -eq "roundrobin") {
    Write-TestHeader "GROUP: Round-Robin Layers"
    
    Invoke-Test -Name "Round-robin: 2 layers, single note" -Group "roundrobin" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--roundrobin_layers", "2", "--multisample_name", "test_rr_basic")) `
        -ExpectedSamples 2
    
    Invoke-Test -Name "Round-robin: 2 layers × 4 notes" -Group "roundrobin" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C5", "--note_range_interval", "12", "--roundrobin_layers", "2", "--multisample_name", "test_rr_noterange")) `
        -ExpectedSamples 4
}

# Group: Combined Tests
if (($Group -eq "all" -or $Group -eq "combined") -and -not $Quick) {
    Write-TestHeader "GROUP: Combined Velocity + Round-Robin"
    
    Invoke-Test -Name "Combined: 3 velocity × 2 RR, single note" -Group "combined" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--velocity_layers", "3", "--roundrobin_layers", "2", "--multisample_name", "test_vel_rr_combined")) `
        -ExpectedSamples 6
    
    Invoke-Test -Name "Combined: 2 velocity × 2 RR × 3 notes" -Group "combined" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "E4", "--note_range_interval", "2", "--velocity_layers", "2", "--roundrobin_layers", "2", "--multisample_name", "test_full_combo")) `
        -ExpectedSamples 12
}

# Group: Audio Configuration Tests
if (($Group -eq "all" -or $Group -eq "audio") -and -not $Quick) {
    Write-TestHeader "GROUP: Audio Configuration"
    
    Invoke-Test -Name "Audio: Mono left channel" -Group "audio" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--mono_stereo", "mono", "--mono_channel", "0", "--multisample_name", "test_mono_left")) `
        -ExpectedSamples 1
    
    Invoke-Test -Name "Audio: Mono right channel" -Group "audio" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--mono_stereo", "mono", "--mono_channel", "1", "--multisample_name", "test_mono_right")) `
        -ExpectedSamples 1
    
    Invoke-Test -Name "Audio: Stereo recording" -Group "audio" `
        -Arguments ($baseArgs + @("--note_range_start", "C4", "--note_range_end", "C4", "--note_range_interval", "1", "--mono_stereo", "stereo", "--multisample_name", "test_stereo")) `
        -ExpectedSamples 1
}

# Group: Metadata Verification
if (($Group -eq "all" -or $Group -eq "metadata") -and -not $Quick) {
    Write-TestHeader "GROUP: WAV Metadata Verification"
    
    $testDir = "output\test_single_C4_cli\samples"
    if (Test-Path $testDir) {
        $wavFiles = Get-ChildItem $testDir -Filter "*.wav"
        if ($wavFiles.Count -gt 0) {
            $testFile = $wavFiles[0].FullName
            Write-Host "`nVerifying WAV metadata for: $($wavFiles[0].Name)" -ForegroundColor Gray
            
            $testStart = Get-Date
            try {
                $output = & python verify_wav_metadata.py $testFile 2>&1
                $exitCode = $LASTEXITCODE
                $duration = (Get-Date) - $testStart
                $durationSec = $duration.TotalSeconds
                
                $output | ForEach-Object { Write-Host $_ }
                
                $passed = ($exitCode -eq 0) -and ($output -match "Note Chunk Found")
                $errorMsg = if ($passed) { "3-byte format verified" } else { "Metadata verification failed" }
                
                Write-TestResult -Name "WAV metadata format" -Group "metadata" -Passed $passed -Duration $durationSec -ErrorMsg $errorMsg
            } catch {
                $duration = (Get-Date) - $testStart
                Write-TestResult -Name "WAV metadata format" -Group "metadata" -Passed $false -Duration $duration.TotalSeconds -ErrorMsg $_.Exception.Message
            }
        } else {
            Write-Host "⊘ SKIPPED - No WAV files found" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⊘ SKIPPED - Test output directory not found" -ForegroundColor Yellow
    }
}

# Print Summary
$totalDuration = (Get-Date) - $script:StartTime
Write-Host "`n$('='*60)" -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "$('='*60)" -ForegroundColor Cyan

Write-Host "`nTotal: $script:TotalTests | " -NoNewline
Write-Host "Passed: $script:PassedTests" -ForegroundColor Green -NoNewline
Write-Host " | " -NoNewline
Write-Host "Failed: $script:FailedTests" -ForegroundColor Red
Write-Host "Total time: $([math]::Round($totalDuration.TotalSeconds, 1))s"

if ($script:FailedTests -gt 0) {
    Write-Host "`nFailed tests:" -ForegroundColor Red
    $script:TestResults | Where-Object { -not $_.Passed } | ForEach-Object {
        Write-Host "  ✗ $($_.Name) ($($_.Group))" -ForegroundColor Red
        if ($_.Error) {
            Write-Host "    Error: $($_.Error)" -ForegroundColor Red
        }
    }
}

# Group summary
Write-Host "`nTest groups summary:"
$groupStats = $script:TestResults | Group-Object Group | ForEach-Object {
    $total = $_.Count
    $passed = ($_.Group | Where-Object { $_.Passed }).Count
    [PSCustomObject]@{
        Group = $_.Name
        Passed = $passed
        Total = $total
        Status = if ($passed -eq $total) { "✓" } else { "✗" }
    }
}

$groupStats | Sort-Object Group | ForEach-Object {
    $color = if ($_.Status -eq "✓") { "Green" } else { "Red" }
    Write-Host "  $($_.Status) $($_.Group): $($_.Passed)/$($_.Total)" -ForegroundColor $color
}

Write-Host "$('='*60)" -ForegroundColor Cyan

# Exit with appropriate code
exit $(if ($script:FailedTests -eq 0) { 0 } else { 1 })
