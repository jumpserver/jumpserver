$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

function Assert-TransferPath([string]$Path, [bool]$Directory) {
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = $root.TrimEnd('\') + '\'
    if (!$full.Equals($root, [StringComparison]::OrdinalIgnoreCase) -and
        !$full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'outside_root' }
    $item = Get-Item -LiteralPath $full -Force
    if ($item.PSIsContainer -ne $Directory) { throw 'invalid_file_type' }
    $cursor = $full
    while ($cursor) {
        $entry = Get-Item -LiteralPath $cursor -Force
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'symlink_not_allowed' }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
    return $item
}

$p = $null
$stream = $null
$hasher = $null
$created = $false
$committed = $false
$result = $null
try {
    while ($null -ne ($line = [Console]::In.ReadLine())) {
        if ($null -eq $p) {
            $p = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($line)) | ConvertFrom-Json
            $root = if ($p.root -eq 'home') { $env:USERPROFILE } else { $p.root }
            $root = [IO.Path]::GetFullPath($root)
            if ($root.Length -gt 3) { $root = $root.TrimEnd('\') }
            if ($p.action -eq 'root') {
                $null = Assert-TransferPath $root $true
                $result = @{root = $root}
            } elseif ($p.action -eq 'upload') {
                $parent = [IO.Path]::GetDirectoryName($p.path)
                $null = Assert-TransferPath $parent $true
                if (Test-Path -LiteralPath $p.path) { throw 'destination_exists' }
                $stream = [IO.File]::Open($p.temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
                $created = $true
                $hasher = [Security.Cryptography.SHA256]::Create()
                $size = 0L
            } else {
                $item = Assert-TransferPath $p.path $false
                $result = @{size = $item.Length; mtime = $item.LastWriteTimeUtc.Ticks.ToString()}
                if ($p.action -eq 'read') {
                    if ($item.Length -ne $p.size -or $result.mtime -ne $p.mtime) { throw 'source_changed' }
                    $stream = [IO.File]::Open($p.path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
                    $null = $stream.Seek([long]$p.offset, [IO.SeekOrigin]::Begin)
                    $buffer = New-Object byte[] ([int]$p.count)
                    $read = 0
                    while ($read -lt $buffer.Length) {
                        $count = $stream.Read($buffer, $read, $buffer.Length - $read)
                        if (!$count) { break }
                        $read += $count
                    }
                    $result = @{data = [Convert]::ToBase64String($buffer, 0, $read)}
                } elseif ($p.action -ne 'stat') { throw 'transfer_failed' }
            }
        } elseif ($p.action -eq 'upload' -and !$committed) {
            if ($line -eq 'COMMIT') {
                $null = $hasher.TransformFinalBlock([byte[]]@(), 0, 0)
                $hash = [BitConverter]::ToString($hasher.Hash).Replace('-', '').ToLowerInvariant()
                if ($size -ne $p.size -or $hash -ne $p.sha256) { throw 'source_changed' }
                $stream.Dispose()
                $stream = $null
                $null = Assert-TransferPath $parent $true
                $null = Assert-TransferPath $p.temporary $false
                if (Test-Path -LiteralPath $p.path) { throw 'destination_exists' }
                # The two-argument Move never overwrites an existing destination.
                [IO.File]::Move($p.temporary, $p.path)
                $committed = $true
                $result = @{size = $size; sha256 = $hash}
            } else {
                $bytes = [Convert]::FromBase64String($line)
                $size += $bytes.Length
                if ($size -gt $p.limit -or $size -gt $p.size) { throw 'size_limit' }
                $null = $hasher.TransformBlock($bytes, 0, $bytes.Length, $bytes, 0)
                $stream.Write($bytes, 0, $bytes.Length)
            }
        } else { throw 'transfer_failed' }
    }
    if (!$result -or ($p.action -eq 'upload' -and !$committed)) { throw 'transfer_failed' }
} catch {
    $code = $_.Exception.Message
    if ($_.Exception -is [UnauthorizedAccessException]) { $code = 'permission_denied' }
    elseif ($_.CategoryInfo.Category -eq 'ObjectNotFound') { $code = 'file_missing' }
    $allowed = @('outside_root', 'symlink_not_allowed', 'invalid_file_type', 'destination_exists',
                 'source_changed', 'size_limit', 'file_missing', 'permission_denied')
    if ($code -notin $allowed) { $code = 'transfer_failed' }
    $result = @{error = $code}
} finally {
    if ($stream) { $stream.Dispose() }
    if ($hasher) { $hasher.Dispose() }
    if ($created -and !$committed) {
        try {
            $null = Assert-TransferPath $parent $true
            $null = Assert-TransferPath $p.temporary $false
            [IO.File]::Delete($p.temporary)
        } catch {}
    }
}
$result | ConvertTo-Json -Compress
