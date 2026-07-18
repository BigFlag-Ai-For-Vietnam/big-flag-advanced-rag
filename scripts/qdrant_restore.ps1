# Khôi phục collection Qdrant "rag_chunks" từ snapshot đã commit trong repo.
# Dùng sau khi clone/pull + `docker compose up -d` (Qdrant khởi động rỗng, named volume).
#
#   powershell -ExecutionPolicy Bypass -File scripts/qdrant_restore.ps1
#
$ErrorActionPreference = "Stop"
$col = "rag_chunks"
$snap = Join-Path $PSScriptRoot "..\qdrant_snapshots\rag_chunks.snapshot"
if (-not (Test-Path $snap)) { throw "Không thấy snapshot: $snap" }

# Chờ Qdrant sẵn sàng
for ($i = 0; $i -lt 20; $i++) {
  try { Invoke-RestMethod "http://localhost:6333/" -TimeoutSec 3 | Out-Null; break } catch { Start-Sleep 2 }
}

Write-Host "Uploading snapshot -> collection '$col' ..."
# priority=snapshot: dữ liệu trong snapshot thắng khi có xung đột
& curl.exe -s -X POST "http://localhost:6333/collections/$col/snapshots/upload?priority=snapshot" `
  -F "snapshot=@$snap" | Write-Host

$c = Invoke-RestMethod "http://localhost:6333/collections/$col"
Write-Host "`nDone. points_count = $($c.result.points_count)"
