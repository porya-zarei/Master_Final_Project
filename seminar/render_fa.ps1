param([string]$Pptx = "E:\Education\Master\Final_Project\seminar\Seminar_I_Pouria_Zarei_FA.pptx",
      [string]$OutDir = "E:\Education\Master\Final_Project\seminar\render_fa")

$ErrorActionPreference = "Stop"
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Force $OutDir | Out-Null

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.DisplayAlerts = 1
$pres = $ppt.Presentations.Open($Pptx, -1, 0, 0)
"slides: " + $pres.Slides.Count
for ($i = 1; $i -le $pres.Slides.Count; $i++) {
    $n = $pres.Slides.Item($i).TimeLine.MainSequence.Count
    "slide {0}: {1} animation steps" -f $i, $n
}
$pres.Export($OutDir, "PNG", 1920, 1080)
$pres.Close()
$ppt.Quit()
"exported to $OutDir"
