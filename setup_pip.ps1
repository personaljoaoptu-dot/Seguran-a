Write-Host "Downloading get-pip.py..."
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"

Write-Host "Installing pip..."
$process = Start-Process -FilePath ".\python311\python.exe" -ArgumentList "get-pip.py" -Wait -NoNewWindow -PassThru

if ($process.ExitCode -eq 0) {
    Write-Host "pip installed successfully! Installing pg8000 and scramp..."
    $process2 = Start-Process -FilePath ".\python311\python.exe" -ArgumentList "-m pip install pg8000 scramp" -Wait -NoNewWindow -PassThru
    if ($process2.ExitCode -eq 0) {
        Write-Host "pg8000 and scramp installed successfully!"
    } else {
        Write-Host "Failed to install pg8000/scramp. Exit code: $($process2.ExitCode)"
    }
} else {
    Write-Host "Failed to install pip. Exit code: $($process.ExitCode)"
}
