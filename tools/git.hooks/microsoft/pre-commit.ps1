# Iterate over each file in the git diff --cached output
git diff --name-only --cached | ForEach-Object {
    $f = $_
    # Check if the file has an .ipynb extension
    if ($f -like '*.ipynb') {
        # Clear the output of the Jupyter notebook in-place
        jupyter nbconvert --clear-output --inplace $f
        # Add the modified file back to the git index
        git add $f
    }
}

# Check if there are any differences in the git index after clearing outputs
if (-not (git diff --name-only --cached)) {
    Write-Output "No changes detected after removing notebook output"
    exit 1
}
