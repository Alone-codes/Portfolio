for ($i = 1; $i -le 10; $i++) {
    $date = "2025-10-$i 10:00:00"

    Add-Content file.txt "update $i"
    git add .

    $env:GIT_AUTHOR_DATE = $date
    $env:GIT_COMMITTER_DATE = $date

    git commit -m "update $i"
}