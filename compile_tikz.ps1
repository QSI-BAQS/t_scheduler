# Define the directory containing the .tex files
$directory = "out"

# Change to the target directory
Set-Location -Path $directory

# Get all .tex files in the directory
$texFiles = Get-ChildItem -Filter "*.tex"

# Store the current directory to pass to thread jobs
$currentDirectory = Get-Location

# Run thread jobs with ThrottleLimit
$jobs = foreach ($texFile in $texFiles) {
    Start-ThreadJob -ScriptBlock {
        param ($filePath, $workingDir)

        $env:PATH = ($env:PATH -split ';' | Where-Object { $_ -ne "C:\Users\Admin\AppData\Roaming\TinyTeX\bin\windows" }) -join ';'

        # Change to the original working directory
        Set-Location -Path $workingDir

        # Run pdflatex on the file
        pdflatex -interaction=nonstopmode $filePath > $null 2>&1

        # Output success message
        Write-Output "Successfully compiled $filePath"
    } -ArgumentList $texFile.FullName, $currentDirectory.Path -ThrottleLimit 10
}

# Wait for all thread jobs to complete
Write-Host "Waiting for all jobs to finish..."

# Retrieve and display the output from each job
foreach ($job in $jobs) {
    Wait-Job -Job $job
    $output = Receive-Job -Job $job
    Write-Host $output
    Remove-Job -Job $job
}

Write-Host "All .tex files have been processed."
