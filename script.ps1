$startDate = Get-Date "2025-03-25"
$endDate = Get-Date

$currentDate = $startDate

while ($currentDate -le $endDate) {

    # Random commits per day: 0 to 4
    $commits = Get-Random -Minimum 0 -Maximum 5

    for ($i = 1; $i -le $commits; $i++) {

        # Random hour/min/sec for natural look
        $hour = Get-Random -Minimum 9 -Maximum 22
        $minute = Get-Random -Minimum 0 -Maximum 60
        $second = Get-Random -Minimum 0 -Maximum 60

        $dateString = $currentDate.ToString("yyyy-MM-dd") + " $hour`:$minute`:$second"

        Add-Content file.txt "update $dateString"
        git add .

        $env:GIT_AUTHOR_DATE = $dateString
        $env:GIT_COMMITTER_DATE = $dateString

        git commit -m "update on $dateString"
    }

    # Move to next day
    $currentDate = $currentDate.AddDays(1)
}