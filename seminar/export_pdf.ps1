param([string]$Pptx = "E:\Education\Master\Final_Project\seminar\Seminar_I_Pouria_Zarei.pptx",
      [string]$Pdf = "E:\Education\Master\Final_Project\seminar\Seminar_I_Pouria_Zarei.pdf")

$ErrorActionPreference = "Stop"
$ppt = New-Object -ComObject PowerPoint.Application
$ppt.DisplayAlerts = 1
$pres = $ppt.Presentations.Open($Pptx, -1, 0, 0)
$pres.SaveAs($Pdf, 32)   # ppSaveAsPDF
$pres.Close()
$ppt.Quit()
"PDF: " + (Get-Item $Pdf).Length
