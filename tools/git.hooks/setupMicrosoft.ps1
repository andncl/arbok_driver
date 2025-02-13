# Get the top-level directory of the git repository
$topLevelDir = git rev-parse --show-toplevel

# Change the directory to the .git/hooks directory
Push-Location "$topLevelDir/.git/hooks"

# Create a symbolic link
# New-Item -ItemType SymbolicLink -Path 'pre-commit' -Target '../../tools/github.hooks/microsoft/pre-commit'
# hard copy
cp '..\..\tools\git.hooks\microsoft\pre-commit' .
# need to set the file to executable
# The following tests executable ()
Test-Path $PSHOME\pwsh.exe, .\pre-commit
Pop-Location