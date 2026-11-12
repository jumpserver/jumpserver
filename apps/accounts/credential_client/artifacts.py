"""Versioned public downloads built from Core's pinned clients submodule."""
from urllib.parse import urljoin
from shlex import quote

from django.templatetags.static import static

from accounts.clients.distribution import client_version


def artifact_url(filename, endpoint=''):
    path = static(f'pam/{client_version()}/{filename}')
    return urljoin(endpoint.rstrip('/') + '/', path) if endpoint else path


def agent_download_command(endpoint):
    base = artifact_url('', endpoint).rstrip('/')
    return f'''(\nset -e
case "$(uname -s)" in
  Linux) agent_os=linux ;;
  Darwin) agent_os=darwin ;;
  *) echo "Unsupported operating system" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) agent_arch=amd64 ;;
  aarch64|arm64) agent_arch=arm64 ;;
  *) echo "Unsupported CPU architecture" >&2; exit 1 ;;
esac
agent_file="pam-agent-$agent_os-$agent_arch"
curl -fL {quote(base + '/')}"$agent_file" -o "$agent_file"
curl -fL {quote(base + '/SHA256SUMS')} -o SHA256SUMS
awk -v file="$agent_file" '$2 == file {{ print; found=1 }} END {{ if (!found) exit 1 }}' SHA256SUMS > "$agent_file.sha256"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum --check "$agent_file.sha256"
else
  shasum -a 256 --check "$agent_file.sha256"
fi
install -m 0755 "$agent_file" ./pam-agent
)'''


def windows_agent_download_command(endpoint):
    base = artifact_url('', endpoint).rstrip('/').replace("'", "''")
    return f'''$ErrorActionPreference = 'Stop'
$agentArchitectures = @{{ X64 = 'amd64'; Arm64 = 'arm64' }}
$agentArch = $agentArchitectures[[System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()]
if (-not $agentArch) {{ throw 'Unsupported CPU architecture' }}
$agentFile = "pam-agent-windows-$agentArch.exe"
Invoke-WebRequest -Uri ('{base}/' + $agentFile) -OutFile $agentFile
Invoke-WebRequest -Uri '{base}/SHA256SUMS' -OutFile './SHA256SUMS'
$checksum = @(Get-Content './SHA256SUMS' | Where-Object {{ ($_ -split '\\s+')[1] -eq $agentFile }})
if ($checksum.Count -ne 1) {{ throw 'Missing or duplicate Agent checksum' }}
$expected = ($checksum[0] -split '\\s+')[0]
if ((Get-FileHash $agentFile -Algorithm SHA256).Hash -ne $expected) {{ throw 'Agent checksum mismatch' }}
Move-Item -LiteralPath $agentFile -Destination './pam-agent.exe' -Force'''
