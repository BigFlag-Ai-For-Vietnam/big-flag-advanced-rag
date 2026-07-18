# Tạo snapshot mới của collection "rag_chunks" và cập nhật file commit
# qdrant_snapshots/rag_chunks.snapshot. Chạy sau khi (re)index để đẩy data mới lên git.
#
#   powershell -ExecutionPolicy Bypass -File scripts/qdrant_snapshot.ps1
#   git add qdrant_snapshots/rag_chunks.snapshot && git commit -m "data: refresh qdrant snapshot"
#
$ErrorActionPreference = "Stop"
$col = "rag_chunks"
$out = Join-Path $PSScriptRoot "..\qdrant_snapshots\rag_chunks.snapshot"

Write-Host "Creating snapshot for '$col' ..."
$r = Invoke-RestMethod -Method Post "http://localhost:6333/collections/$col/snapshots" -TimeoutSec 120
$name = $r.result.name

# Tải snapshot qua API về đúng file ổn định (không phụ thuộc bind mount)
Invoke-WebRequest "http://localhost:6333/collections/$col/snapshots/$name" -OutFile $out -TimeoutSec 120
$kb = [math]::Round((Get-Item $out).Length / 1KB, 1)
Write-Host "Updated $out ($kb KB). Nhớ: git add + commit để đẩy lên."

# Dọn snapshot timestamped trên server cho gọn (không bắt buộc)
try { Invoke-RestMethod -Method Delete "http://localhost:6333/collections/$col/snapshots/$name" | Out-Null } catch {}
