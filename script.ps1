$startDate = Get-Date "2025-10-24"
$endDate = Get-Date

$currentDate = $startDate

while ($currentDate -le $endDate) {

    # Random working streak (3–5 days)
    $workDays = Get-Random -Minimum 3 -Maximum 6

    for ($w = 0; $w -lt $workDays -and $currentDate -le $endDate; $w++) {

        # Random commits per day (1–4) → avoid too many 0 days inside streak
        $commits = Get-Random -Minimum 1 -Maximum 5

        for ($i = 1; $i -le $commits; $i++) {

            # Random time (more realistic working hours)
            $hour = Get-Random -Minimum 10 -Maximum 21
            $minute = Get-Random -Minimum 0 -Maximum 60
            $second = Get-Random -Minimum 0 -Maximum 60

            $dateString = $currentDate.ToString("yyyy-MM-dd") + " $hour`:$minute`:$second"

            Add-Content file.txt "update $dateString"
            git add .

            $env:GIT_AUTHOR_DATE = $dateString
            $env:GIT_COMMITTER_DATE = $dateString

            git commit -m "update on $dateString"
        }

        # Move to next working day
        $currentDate = $currentDate.AddDays(1)
    }

    # Random skip days (1–3 days)
    $skipDays = Get-Random -Minimum 1 -Maximum 4
    $currentDate = $currentDate.AddDays($skipDays)
}