<#
.SYNOPSIS
    Finds and organizes common media and document files into a central archive.
.DESCRIPTION
    Opens a Windows Forms interface by default. Use -Cli for the command-line
    workflow. Files are never deleted by this script.
.EXAMPLE
    .\FileOrganizer.ps1
.EXAMPLE
    .\FileOrganizer.ps1 -Cli -SourcePaths 'C:\Users\name\Downloads','D:\Media' -DestinationPath 'E:\Master_Archive'
.EXAMPLE
    .\FileOrganizer.ps1 -Cli -Apply
#>
param(
    [string[]]$SourcePaths = @('C:\', 'D:\', 'E:\'),
    [string]$DestinationPath = 'E:\Master_Archive',
    [switch]$Apply,
    [switch]$Cli
)

if (-not $Cli) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()

    $guiCategoryByExtension = @{
        '.pdf' = 'Documents'; '.doc' = 'Documents'; '.docx' = 'Documents'
        '.txt' = 'Documents'; '.rtf' = 'Documents'; '.odt' = 'Documents'
        '.xls' = 'Documents'; '.xlsx' = 'Documents'; '.csv' = 'Documents'
        '.ppt' = 'Documents'; '.pptx' = 'Documents'
        '.jpg' = 'Images'; '.jpeg' = 'Images'; '.png' = 'Images'
        '.gif' = 'Images'; '.bmp' = 'Images'; '.tif' = 'Images'; '.tiff' = 'Images'
        '.webp' = 'Images'; '.heic' = 'Images'; '.raw' = 'Images'; '.dng' = 'Images'
        '.wav' = 'Audio'; '.mp3' = 'Audio'; '.midi' = 'Audio'; '.mid' = 'Audio'
        '.flp' = 'Audio'; '.als' = 'Audio'; '.aiff' = 'Audio'; '.aif' = 'Audio'
        '.flac' = 'Audio'; '.m4a' = 'Audio'; '.ogg' = 'Audio'; '.wma' = 'Audio'
        '.aac' = 'Audio'; '.opus' = 'Audio'
        '.mp4' = 'Video'; '.mkv' = 'Video'; '.avi' = 'Video'; '.mov' = 'Video'
        '.wmv' = 'Video'; '.m4v' = 'Video'; '.mpeg' = 'Video'; '.mpg' = 'Video'
        '.webm' = 'Video'; '.3gp' = 'Video'
    }
    $guiExcludedDirectorySet = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    foreach ($name in @(
        'Windows', 'Program Files', 'Program Files (x86)', 'ProgramData', 'AppData',
        'System Volume Information', '$RECYCLE.BIN', 'SteamLibrary', 'VSTPlugins',
        'Steinberg', 'User Library', 'World of Warcraft', 'Guild Wars', 'Fortnite',
        'AmongUs', 'Dragonball'
    )) {
        [void]$guiExcludedDirectorySet.Add($name)
    }

    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'File Organizer'
    $form.StartPosition = 'CenterScreen'
    $form.ClientSize = [System.Drawing.Size]::new(1180, 760)
    $form.MinimumSize = [System.Drawing.Size]::new(980, 650)
    $form.BackColor = [System.Drawing.Color]::FromArgb(245, 247, 246)
    $form.Font = [System.Drawing.Font]::new('Segoe UI', 9)

    $layout = New-Object System.Windows.Forms.TableLayoutPanel
    $layout.Dock = 'Fill'
    $layout.Padding = [System.Windows.Forms.Padding]::new(18)
    $layout.ColumnCount = 1
    $layout.RowCount = 3
    [void]$layout.RowStyles.Add([System.Windows.Forms.RowStyle]::new('Absolute', 76))
    [void]$layout.RowStyles.Add([System.Windows.Forms.RowStyle]::new('Percent', 100))
    [void]$layout.RowStyles.Add([System.Windows.Forms.RowStyle]::new('Absolute', 64))
    $form.Controls.Add($layout)

    $header = New-Object System.Windows.Forms.Panel
    $header.Dock = 'Fill'
    $header.BackColor = [System.Drawing.Color]::FromArgb(25, 61, 58)
    $title = New-Object System.Windows.Forms.Label
    $title.Text = 'FILE ORGANIZER'
    $title.ForeColor = [System.Drawing.Color]::White
    $title.Font = [System.Drawing.Font]::new('Segoe UI Semibold', 17)
    $title.Location = [System.Drawing.Point]::new(18, 12)
    $title.AutoSize = $true
    $header.Controls.Add($title)
    $subtitle = New-Object System.Windows.Forms.Label
    $subtitle.Text = 'Review your files before anything is moved. Nothing is deleted.'
    $subtitle.ForeColor = [System.Drawing.Color]::FromArgb(206, 224, 219)
    $subtitle.Location = [System.Drawing.Point]::new(20, 45)
    $subtitle.AutoSize = $true
    $header.Controls.Add($subtitle)
    $layout.Controls.Add($header, 0, 0)

    $main = New-Object System.Windows.Forms.TableLayoutPanel
    $main.Dock = 'Fill'
    $main.ColumnCount = 2
    $main.RowCount = 1
    [void]$main.ColumnStyles.Add([System.Windows.Forms.ColumnStyle]::new('Absolute', 330))
    [void]$main.ColumnStyles.Add([System.Windows.Forms.ColumnStyle]::new('Percent', 100))
    $layout.Controls.Add($main, 0, 1)

    $settings = New-Object System.Windows.Forms.Panel
    $settings.Dock = 'Fill'
    $settings.BackColor = [System.Drawing.Color]::White
    $settings.Padding = [System.Windows.Forms.Padding]::new(14)
    $main.Controls.Add($settings, 0, 0)

    $sourceLabel = New-Object System.Windows.Forms.Label
    $sourceLabel.Text = 'SOURCE FOLDERS'
    $sourceLabel.Location = [System.Drawing.Point]::new(14, 12)
    $sourceLabel.Size = [System.Drawing.Size]::new(285, 22)
    $sourceLabel.Font = [System.Drawing.Font]::new('Segoe UI Semibold', 9)
    $settings.Controls.Add($sourceLabel)

    $sourceList = New-Object System.Windows.Forms.ListBox
    $sourceList.Location = [System.Drawing.Point]::new(14, 38)
    $sourceList.Size = [System.Drawing.Size]::new(285, 112)
    $sourceList.Anchor = 'Top,Left,Right'
    $settings.Controls.Add($sourceList)

    $addSourceButton = New-Object System.Windows.Forms.Button
    $addSourceButton.Text = 'Add folder'
    $addSourceButton.Location = [System.Drawing.Point]::new(14, 158)
    $addSourceButton.Size = [System.Drawing.Size]::new(136, 32)
    $settings.Controls.Add($addSourceButton)
    $removeSourceButton = New-Object System.Windows.Forms.Button
    $removeSourceButton.Text = 'Remove selected'
    $removeSourceButton.Location = [System.Drawing.Point]::new(158, 158)
    $removeSourceButton.Size = [System.Drawing.Size]::new(141, 32)
    $settings.Controls.Add($removeSourceButton)

    $destinationLabel = New-Object System.Windows.Forms.Label
    $destinationLabel.Text = 'ARCHIVE DESTINATION'
    $destinationLabel.Location = [System.Drawing.Point]::new(14, 207)
    $destinationLabel.Size = [System.Drawing.Size]::new(285, 22)
    $destinationLabel.Font = [System.Drawing.Font]::new('Segoe UI Semibold', 9)
    $settings.Controls.Add($destinationLabel)
    $destinationText = New-Object System.Windows.Forms.TextBox
    $destinationText.Location = [System.Drawing.Point]::new(14, 234)
    $destinationText.Size = [System.Drawing.Size]::new(285, 26)
    $destinationText.Anchor = 'Top,Left,Right'
    $settings.Controls.Add($destinationText)
    $browseDestinationButton = New-Object System.Windows.Forms.Button
    $browseDestinationButton.Text = 'Choose destination...'
    $browseDestinationButton.Location = [System.Drawing.Point]::new(14, 268)
    $browseDestinationButton.Size = [System.Drawing.Size]::new(285, 32)
    $browseDestinationButton.Anchor = 'Top,Left,Right'
    $settings.Controls.Add($browseDestinationButton)

    $categoryLabel = New-Object System.Windows.Forms.Label
    $categoryLabel.Text = 'FILE CATEGORIES'
    $categoryLabel.Location = [System.Drawing.Point]::new(14, 316)
    $categoryLabel.Size = [System.Drawing.Size]::new(285, 22)
    $categoryLabel.Font = [System.Drawing.Font]::new('Segoe UI Semibold', 9)
    $settings.Controls.Add($categoryLabel)

    $categoryChecks = @{}
    $categoryPositions = @{
        Documents = [System.Drawing.Point]::new(14, 344)
        Images = [System.Drawing.Point]::new(158, 344)
        Audio = [System.Drawing.Point]::new(14, 374)
        Video = [System.Drawing.Point]::new(158, 374)
    }
    foreach ($categoryName in @('Documents', 'Images', 'Audio', 'Video')) {
        $check = New-Object System.Windows.Forms.CheckBox
        $check.Text = $categoryName
        $check.Checked = $true
        $check.Location = $categoryPositions[$categoryName]
        $check.Size = [System.Drawing.Size]::new(130, 24)
        $settings.Controls.Add($check)
        $categoryChecks[$categoryName] = $check
    }

    $skipProtectedCheck = New-Object System.Windows.Forms.CheckBox
    $skipProtectedCheck.Text = 'Skip common system and app folders'
    $skipProtectedCheck.Checked = $true
    $skipProtectedCheck.Location = [System.Drawing.Point]::new(14, 414)
    $skipProtectedCheck.Size = [System.Drawing.Size]::new(285, 26)
    $settings.Controls.Add($skipProtectedCheck)

    $settingsNote = New-Object System.Windows.Forms.Label
    $settingsNote.Text = 'Scans are previews. Choose which results to include before moving.'
    $settingsNote.Location = [System.Drawing.Point]::new(14, 452)
    $settingsNote.Size = [System.Drawing.Size]::new(285, 48)
    $settingsNote.ForeColor = [System.Drawing.Color]::FromArgb(91, 105, 102)
    $settingsNote.Anchor = 'Top,Left,Right'
    $settings.Controls.Add($settingsNote)

    $results = New-Object System.Windows.Forms.TableLayoutPanel
    $results.Dock = 'Fill'
    $results.Padding = [System.Windows.Forms.Padding]::new(16, 10, 0, 0)
    $results.ColumnCount = 1
    $results.RowCount = 2
    [void]$results.RowStyles.Add([System.Windows.Forms.RowStyle]::new('Absolute', 52))
    [void]$results.RowStyles.Add([System.Windows.Forms.RowStyle]::new('Percent', 100))
    $main.Controls.Add($results, 1, 0)

    $resultsHeader = New-Object System.Windows.Forms.Panel
    $resultsHeader.Dock = 'Fill'
    $resultsTitle = New-Object System.Windows.Forms.Label
    $resultsTitle.Text = 'SCAN PREVIEW'
    $resultsTitle.Font = [System.Drawing.Font]::new('Segoe UI Semibold', 10)
    $resultsTitle.Location = [System.Drawing.Point]::new(0, 4)
    $resultsTitle.Size = [System.Drawing.Size]::new(150, 24)
    $resultsHeader.Controls.Add($resultsTitle)
    $searchText = New-Object System.Windows.Forms.TextBox
    $searchText.Text = 'Filter results'
    $searchText.ForeColor = [System.Drawing.Color]::FromArgb(120, 132, 129)
    $searchText.Size = [System.Drawing.Size]::new(220, 25)
    $searchText.Anchor = 'Top,Right'
    $searchText.Location = [System.Drawing.Point]::new(590, 2)
    $resultsHeader.Controls.Add($searchText)
    $results.Controls.Add($resultsHeader, 0, 0)

    $grid = New-Object System.Windows.Forms.DataGridView
    $grid.Dock = 'Fill'
    $grid.BackgroundColor = [System.Drawing.Color]::White
    $grid.BorderStyle = 'FixedSingle'
    $grid.RowHeadersVisible = $false
    $grid.AllowUserToAddRows = $false
    $grid.AllowUserToDeleteRows = $false
    $grid.AllowUserToResizeRows = $false
    $grid.MultiSelect = $false
    $grid.SelectionMode = 'FullRowSelect'
    $grid.AutoSizeColumnsMode = 'Fill'
    $grid.EditMode = 'EditOnEnter'
    $grid.ColumnHeadersHeight = 36
    $grid.EnableHeadersVisualStyles = $false
    $grid.ColumnHeadersDefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(232, 238, 236)
    $grid.ColumnHeadersDefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(35, 51, 48)
    $grid.DefaultCellStyle.SelectionBackColor = [System.Drawing.Color]::FromArgb(213, 231, 224)
    $grid.DefaultCellStyle.SelectionForeColor = [System.Drawing.Color]::FromArgb(25, 45, 41)
    $includeColumn = New-Object System.Windows.Forms.DataGridViewCheckBoxColumn
    $includeColumn.Name = 'Include'
    $includeColumn.HeaderText = 'Move'
    $includeColumn.FillWeight = 45
    [void]$grid.Columns.Add($includeColumn)
    foreach ($columnSpec in @(
        @('Category', 'Category', 75), @('Name', 'File name', 90),
        @('Source', 'Current location', 155), @('Destination', 'New location', 155),
        @('Size', 'Size', 50)
    )) {
        $column = New-Object System.Windows.Forms.DataGridViewTextBoxColumn
        $column.Name = $columnSpec[0]
        $column.HeaderText = $columnSpec[1]
        $column.FillWeight = [float]$columnSpec[2]
        $column.ReadOnly = $true
        [void]$grid.Columns.Add($column)
    }
    $results.Controls.Add($grid, 0, 1)

    $footer = New-Object System.Windows.Forms.Panel
    $footer.Dock = 'Fill'
    $statusLabel = New-Object System.Windows.Forms.Label
    $statusLabel.Text = 'Add one or more source folders, then scan.'
    $statusLabel.Location = [System.Drawing.Point]::new(2, 20)
    $statusLabel.Size = [System.Drawing.Size]::new(510, 26)
    $statusLabel.Anchor = 'Left,Top,Right'
    $footer.Controls.Add($statusLabel)
    $moveButton = New-Object System.Windows.Forms.Button
    $moveButton.Text = 'Move checked files'
    $moveButton.Enabled = $false
    $moveButton.Size = [System.Drawing.Size]::new(160, 38)
    $moveButton.Location = [System.Drawing.Point]::new(775, 12)
    $moveButton.Anchor = 'Top,Right'
    $footer.Controls.Add($moveButton)
    $scanButton = New-Object System.Windows.Forms.Button
    $scanButton.Text = 'Scan folders'
    $scanButton.Size = [System.Drawing.Size]::new(130, 38)
    $scanButton.Location = [System.Drawing.Point]::new(945, 12)
    $scanButton.Anchor = 'Top,Right'
    $scanButton.BackColor = [System.Drawing.Color]::FromArgb(25, 91, 78)
    $scanButton.ForeColor = [System.Drawing.Color]::White
    $scanButton.FlatStyle = 'Flat'
    $footer.Controls.Add($scanButton)
    $layout.Controls.Add($footer, 0, 2)

    $initialSources = @()
    if ($PSBoundParameters.ContainsKey('SourcePaths')) {
        $initialSources = $SourcePaths
    } else {
        $initialSources = @(
            (Join-Path $HOME 'Downloads'),
            [Environment]::GetFolderPath('MyDocuments'),
            [Environment]::GetFolderPath('Desktop')
        )
    }
    foreach ($path in $initialSources) {
        if ((Test-Path -LiteralPath $path -PathType Container) -and -not $sourceList.Items.Contains($path)) {
            [void]$sourceList.Items.Add($path)
        }
    }
    if ($PSBoundParameters.ContainsKey('DestinationPath')) {
        $destinationText.Text = $DestinationPath
    } else {
        $destinationText.Text = Join-Path $HOME 'Organized Archive'
    }

    $folderDialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $folderDialog.ShowNewFolderButton = $true
    $addSourceButton.Add_Click({
        $folderDialog.Description = 'Choose a folder to scan for supported files.'
        if ($folderDialog.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK -and
            -not $sourceList.Items.Contains($folderDialog.SelectedPath)) {
            [void]$sourceList.Items.Add($folderDialog.SelectedPath)
        }
    }.GetNewClosure())
    $removeSourceButton.Add_Click({
        if ($sourceList.SelectedIndex -ge 0) {
            $sourceList.Items.RemoveAt($sourceList.SelectedIndex)
        }
    }.GetNewClosure())
    $browseDestinationButton.Add_Click({
        $folderDialog.Description = 'Choose where organized files should be placed.'
        if (Test-Path -LiteralPath $destinationText.Text -PathType Container) {
            $folderDialog.SelectedPath = $destinationText.Text
        }
        if ($folderDialog.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK) {
            $destinationText.Text = $folderDialog.SelectedPath
        }
    }.GetNewClosure())

    $searchText.Add_TextChanged({
        $query = if ($searchText.Text -eq 'Filter results') { '' } else { $searchText.Text.Trim() }
        foreach ($row in $grid.Rows) {
            $row.Visible = [string]::IsNullOrWhiteSpace($query) -or
                (($row.Cells['Category'].Value, $row.Cells['Name'].Value,
                  $row.Cells['Source'].Value, $row.Cells['Destination'].Value) -join ' ').
                    IndexOf($query, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        }
    }.GetNewClosure())
    $searchText.Add_GotFocus({
        if ($searchText.Text -eq 'Filter results') {
            $searchText.Text = ''
            $searchText.ForeColor = [System.Drawing.Color]::FromArgb(35, 51, 48)
        }
    }.GetNewClosure())
    $searchText.Add_LostFocus({
        if ([string]::IsNullOrWhiteSpace($searchText.Text)) {
            $searchText.Text = 'Filter results'
            $searchText.ForeColor = [System.Drawing.Color]::FromArgb(120, 132, 129)
        }
    }.GetNewClosure())

    $scanButton.Add_Click({
        $archivePath = $destinationText.Text.Trim()
        if ([string]::IsNullOrWhiteSpace($archivePath)) {
            [System.Windows.Forms.MessageBox]::Show('Choose an archive destination first.', 'Destination required', 'OK', 'Warning') | Out-Null
            return
        }
        if ($sourceList.Items.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show('Add at least one source folder to scan.', 'Sources required', 'OK', 'Warning') | Out-Null
            return
        }
        $enabledCategories = @($categoryChecks.GetEnumerator() | Where-Object { $_.Value.Checked } | ForEach-Object { $_.Key })
        if ($enabledCategories.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show('Select at least one file category.', 'Categories required', 'OK', 'Warning') | Out-Null
            return
        }
        try {
            $archiveFullPath = [System.IO.Path]::GetFullPath($archivePath)
        } catch {
            [System.Windows.Forms.MessageBox]::Show('The destination path is not valid.', 'Invalid destination', 'OK', 'Error') | Out-Null
            return
        }

        $scanButton.Enabled = $false
        $moveButton.Enabled = $false
        $grid.Rows.Clear()
        $statusLabel.Text = 'Scanning folders...'
        $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
        $form.Refresh()
        [System.Windows.Forms.Application]::DoEvents()

        $plan = New-Object System.Collections.Generic.List[object]
        $seenSources = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        $reservedDestinations = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        $scanErrorCount = 0
        $examinedCount = 0
        foreach ($source in @($sourceList.Items)) {
            if (-not (Test-Path -LiteralPath $source -PathType Container)) {
                $scanErrorCount++
                continue
            }
            $sourceErrors = @()
            Get-ChildItem -LiteralPath $source -File -Recurse -ErrorAction SilentlyContinue -ErrorVariable +sourceErrors |
                ForEach-Object {
                    $file = $_
                    $examinedCount++
                    if (($examinedCount % 300) -eq 0) {
                        $statusLabel.Text = "Scanning... $examinedCount files checked"
                        [System.Windows.Forms.Application]::DoEvents()
                    }
                    if (-not $seenSources.Add($file.FullName)) {
                        return
                    }
                    $fullFilePath = [System.IO.Path]::GetFullPath($file.FullName)
                    $archiveRoot = $archiveFullPath.TrimEnd('\')
                    $insideArchive = $fullFilePath.Equals($archiveRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
                        $fullFilePath.StartsWith($archiveRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
                    if ($insideArchive) { return }
                    if ($skipProtectedCheck.Checked) {
                        foreach ($segment in $fullFilePath.Split([char]'\')) {
                            if ($guiExcludedDirectorySet.Contains($segment)) { return }
                        }
                    }
                    $extension = $file.Extension.ToLowerInvariant()
                    if (-not $guiCategoryByExtension.ContainsKey($extension)) { return }
                    $category = $guiCategoryByExtension[$extension]
                    if ($enabledCategories -notcontains $category) { return }

                    $targetDirectory = Join-Path $archiveFullPath $category
                    $targetFile = Join-Path $targetDirectory $file.Name
                    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                    $suffix = 1
                    while ((Test-Path -LiteralPath $targetFile) -or $reservedDestinations.Contains($targetFile)) {
                        $targetFile = Join-Path $targetDirectory ('{0}_{1}{2}' -f $baseName, $suffix, $extension)
                        $suffix++
                    }
                    [void]$reservedDestinations.Add($targetFile)
                    $plan.Add([pscustomobject]@{
                        Category = $category
                        Name = $file.Name
                        Source = $file.FullName
                        Destination = $targetFile
                        Length = $file.Length
                    })
                }
            $scanErrorCount += $sourceErrors.Count
        }

        foreach ($item in $plan) {
            $sizeText = if ($item.Length -ge 1MB) { '{0:N1} MB' -f ($item.Length / 1MB) } else { '{0:N0} KB' -f ($item.Length / 1KB) }
            $rowIndex = $grid.Rows.Add($true, $item.Category, $item.Name, $item.Source, $item.Destination, $sizeText)
            $grid.Rows[$rowIndex].Tag = $item
        }
        $scanButton.Enabled = $true
        $moveButton.Enabled = ($plan.Count -gt 0)
        $form.Cursor = [System.Windows.Forms.Cursors]::Default
        $statusLabel.Text = ("{0} files ready to review{1}" -f $plan.Count, $(if ($scanErrorCount -gt 0) { "; $scanErrorCount folders could not be read" } else { '' }))
        if ($plan.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show('No matching files were found. Try another folder or category.', 'Scan complete', 'OK', 'Information') | Out-Null
        }
    }.GetNewClosure())

    $moveButton.Add_Click({
        $grid.EndEdit()
        $selectedItems = @(
            foreach ($row in $grid.Rows) {
                if ([bool]$row.Cells['Include'].Value) { $row.Tag }
            }
        )
        if ($selectedItems.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show('Check at least one file to move.', 'Nothing selected', 'OK', 'Information') | Out-Null
            return
        }
        $answer = [System.Windows.Forms.MessageBox]::Show(
            ("Move {0} checked files into the selected archive?`r`n`r`nFiles will be moved, not copied. Nothing will be deleted." -f $selectedItems.Count),
            'Confirm file moves', 'YesNo', 'Warning'
        )
        if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) { return }

        $moved = 0
        $failed = 0
        $appliedDestinations = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        foreach ($item in $selectedItems) {
            try {
                if (-not (Test-Path -LiteralPath $item.Source -PathType Leaf)) {
                    throw 'The source file no longer exists.'
                }
                $targetFile = $item.Destination
                if ((Test-Path -LiteralPath $targetFile) -or $appliedDestinations.Contains($targetFile)) {
                    $directory = Split-Path -Parent $item.Destination
                    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($item.Name)
                    $extension = [System.IO.Path]::GetExtension($item.Name)
                    $suffix = 1
                    do {
                        $targetFile = Join-Path $directory ('{0}_{1}{2}' -f $baseName, $suffix, $extension)
                        $suffix++
                    } while ((Test-Path -LiteralPath $targetFile) -or $appliedDestinations.Contains($targetFile))
                }
                $targetDirectory = Split-Path -Parent $targetFile
                if (-not (Test-Path -LiteralPath $targetDirectory -PathType Container)) {
                    New-Item -ItemType Directory -Force -Path $targetDirectory -ErrorAction Stop | Out-Null
                }
                Move-Item -LiteralPath $item.Source -Destination $targetFile -ErrorAction Stop
                [void]$appliedDestinations.Add($targetFile)
                $moved++
            } catch {
                $failed++
            }
        }

        foreach ($row in @($grid.Rows)) {
            if (-not (Test-Path -LiteralPath $row.Tag.Source -PathType Leaf)) {
                $grid.Rows.Remove($row)
            }
        }
        $statusLabel.Text = "Moved $moved files; $failed failed."
        $moveButton.Enabled = ($grid.Rows.Count -gt 0)
        [System.Windows.Forms.MessageBox]::Show(
            ("Moved: {0}`r`nFailed: {1}" -f $moved, $failed),
            'Organization complete', 'OK', $(if ($failed -gt 0) { 'Warning' } else { 'Information' })
        ) | Out-Null
    }.GetNewClosure())

    [void]$form.ShowDialog()
    return
}

$ErrorActionPreference = 'Continue'

$categoryByExtension = @{
    '.pdf' = 'Documents'; '.doc' = 'Documents'; '.docx' = 'Documents'
    '.txt' = 'Documents'; '.rtf' = 'Documents'; '.odt' = 'Documents'
    '.xls' = 'Documents'; '.xlsx' = 'Documents'; '.csv' = 'Documents'
    '.ppt' = 'Documents'; '.pptx' = 'Documents'
    '.jpg' = 'Images'; '.jpeg' = 'Images'; '.png' = 'Images'
    '.gif' = 'Images'; '.bmp' = 'Images'; '.tif' = 'Images'; '.tiff' = 'Images'
    '.webp' = 'Images'; '.heic' = 'Images'; '.raw' = 'Images'; '.dng' = 'Images'
    '.wav' = 'Audio'; '.mp3' = 'Audio'; '.midi' = 'Audio'; '.mid' = 'Audio'
    '.flp' = 'Audio'; '.als' = 'Audio'; '.aiff' = 'Audio'; '.aif' = 'Audio'
    '.flac' = 'Audio'; '.m4a' = 'Audio'; '.ogg' = 'Audio'; '.wma' = 'Audio'
    '.aac' = 'Audio'; '.opus' = 'Audio'
    '.mp4' = 'Video'; '.mkv' = 'Video'; '.avi' = 'Video'; '.mov' = 'Video'
    '.wmv' = 'Video'; '.m4v' = 'Video'; '.mpeg' = 'Video'; '.mpg' = 'Video'
    '.webm' = 'Video'; '.3gp' = 'Video'
}

$excludedDirectoryNames = @(
    'Windows', 'Program Files', 'Program Files (x86)', 'ProgramData', 'AppData',
    'System Volume Information', '$RECYCLE.BIN', 'SteamLibrary', 'VSTPlugins',
    'Steinberg', 'User Library', 'World of Warcraft', 'Guild Wars', 'Fortnite',
    'AmongUs', 'Dragonball'
)
$excludedDirectorySet = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
foreach ($directoryName in $excludedDirectoryNames) {
    [void]$excludedDirectorySet.Add($directoryName)
}

function Test-IsExcludedPath {
    param(
        [string]$Path,
        [string]$ArchiveRoot
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $archive = [System.IO.Path]::GetFullPath($ArchiveRoot).TrimEnd('\')
    if ($fullPath.Equals($archive, [System.StringComparison]::OrdinalIgnoreCase) -or
        $fullPath.StartsWith($archive + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }

    foreach ($segment in $fullPath.Split([char]'\')) {
        if ($excludedDirectorySet.Contains($segment)) {
            return $true
        }
    }
    return $false
}

$archiveRoot = [System.IO.Path]::GetFullPath($DestinationPath)
$plan = [System.Collections.Generic.List[object]]::new()
$reservedDestinations = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
$scanErrors = @()

foreach ($sourcePath in $SourcePaths) {
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Container)) {
        Write-Warning "Source path is unavailable; skipping: $sourcePath"
        continue
    }

    Write-Host "Scanning $sourcePath ..." -ForegroundColor Cyan
    $sourceErrors = @()
    $files = Get-ChildItem -LiteralPath $sourcePath -File -Recurse -ErrorAction SilentlyContinue -ErrorVariable +sourceErrors
    $scanErrors += $sourceErrors

    foreach ($file in $files) {
        if (Test-IsExcludedPath -Path $file.FullName -ArchiveRoot $archiveRoot) {
            continue
        }

        $extension = $file.Extension.ToLowerInvariant()
        if (-not $categoryByExtension.ContainsKey($extension)) {
            continue
        }

        $category = $categoryByExtension[$extension]
        $targetDirectory = Join-Path $archiveRoot $category
        $destinationFile = Join-Path $targetDirectory $file.Name
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $counter = 1

        while ((Test-Path -LiteralPath $destinationFile) -or $reservedDestinations.Contains($destinationFile)) {
            $newName = '{0}_{1}{2}' -f $baseName, $counter, $extension
            $destinationFile = Join-Path $targetDirectory $newName
            $counter++
        }
        [void]$reservedDestinations.Add($destinationFile)

        $plan.Add([pscustomobject]@{
            Category    = $category
            Source      = $file.FullName
            Destination = $destinationFile
        })
    }
}

Write-Host ''
Write-Host ("Planned files: {0}" -f $plan.Count) -ForegroundColor Green
if ($plan.Count -gt 0) {
    $plan | Group-Object Category | Sort-Object Name |
        ForEach-Object { Write-Host ("  {0,-10} {1,6}" -f $_.Name, $_.Count) }
    Write-Host ''
    Write-Host 'Preview (first 30 moves):' -ForegroundColor Yellow
    $plan | Select-Object -First 30 | Format-Table Category, Source, Destination -AutoSize
    if ($plan.Count -gt 30) {
        Write-Host ("...and {0} more. Review the plan by narrowing your source paths." -f ($plan.Count - 30))
    }
} else {
    Write-Host 'No supported files were found.'
}

if ($scanErrors.Count -gt 0) {
    Write-Warning ("Some folders could not be scanned ({0} access or I/O errors). The results may be incomplete." -f $scanErrors.Count)
}

if (-not $Apply) {
    Write-Host "`nPreview only. No files or folders were changed. Run again with -Apply to move the listed files."
    return
}

if ($plan.Count -eq 0) {
    return
}

Write-Host "`nThis will move $($plan.Count) files. No files will be deleted." -ForegroundColor Yellow
$confirmation = Read-Host 'Type ORGANIZE to continue'
if ($confirmation -cne 'ORGANIZE') {
    Write-Host 'Cancelled. No files were moved.' -ForegroundColor Yellow
    return
}

$movedCount = 0
$failedCount = 0
foreach ($item in $plan) {
    try {
        $targetDirectory = Split-Path -Parent $item.Destination
        if (-not (Test-Path -LiteralPath $targetDirectory -PathType Container)) {
            New-Item -ItemType Directory -Force -Path $targetDirectory -ErrorAction Stop | Out-Null
        }
        Move-Item -LiteralPath $item.Source -Destination $item.Destination -ErrorAction Stop
        $movedCount++
        Write-Host "Moved: $($item.Source) -> $($item.Destination)" -ForegroundColor DarkGray
    } catch {
        $failedCount++
        Write-Warning ("Could not move '{0}': {1}" -f $item.Source, $_.Exception.Message)
    }
}

Write-Host "`nOrganization complete. Moved: $movedCount; failed: $failedCount." -ForegroundColor Green