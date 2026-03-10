# AiTao - Installation Guide (Windows Portable)

## Requirements

- Windows 10 or later (x64 or ARM64)
- PowerShell 5.1+ (included in all Windows 10/11 installations)
- Internet connection for first-time setup (~1-2 GB download: Python, Meilisearch, Ollama)

---

## Installation (First Time)

### Step 1 - Download the archive

Go to the [Releases page](https://github.com/shamantao/aitao/releases) and download the archive for your platform:

| Platform | Archive |
|---|---|
| Windows 10/11 x64 (most PCs) | `aitao-vX.Y.Z-windows-x64.zip` |
| Windows ARM64 (Snapdragon / Surface Pro) | `aitao-vX.Y.Z-windows-arm64.zip` |

### Step 2 - Extract the archive

Right-click the zip, click **Extract All**, and choose a folder (e.g. `C:\AiTao`).

### Step 3 - Run the setup script

Open PowerShell in the extracted folder and run:

```powershell
.\setup-portable.ps1
```

> **If PowerShell blocks the script**, run this first:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

The setup downloads Python, Meilisearch and Ollama (~1-2 GB), installs Python packages,
and configures the environment. This takes several minutes on first run.

### Step 4 - Configure AiTao

After setup, the file `aitao\config\config.toml` is generated from the template.
Open it in any text editor and set at minimum:

```toml
[indexing]
include_paths = [
  "C:/Users/YourName/Documents/",
  "C:/Users/YourName/Desktop/",
]
```

---

## Starting AiTao

```powershell
.\start-aitao.ps1
```

Once started, open your browser at: **http://localhost:8200**

---

## Stopping AiTao

```powershell
.\stop-aitao.ps1
```

---

## Updating AiTao

To update to the latest version without losing your data or configuration:

```powershell
.\update-aitao.ps1
```

Then restart:

```powershell
.\stop-aitao.ps1
.\start-aitao.ps1
```

To also check pre-release versions:

```powershell
.\update-aitao.ps1 -IncludePrerelease
```

> Your `data\` folder and `aitao\config\config.toml` are **never modified** during an update.

---

## Uninstalling AiTao

```powershell
.\uninstall-aitao.ps1
```

The script stops all services and prompts before deleting data.
To remove everything, delete the AiTao folder afterwards.

---

## Common Problems

### "PowerShell blocks the script"

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### "Port already in use"

Another application is using port 8200 (AiTao API), 7700 (Meilisearch) or 11434 (Ollama).
Stop the conflicting application or change the ports in `aitao\config\config.toml`.

### "Ollama does not start"

On ARM64, Ollama runs in native ARM64 mode. No WSL or Hyper-V required.

Run manually to see the error:

```powershell
.\ollama\ollama.exe serve
```

### "Setup fails during Python package installation"

Ensure you have an active internet connection.
For x64, LanceDB requires the Visual C++ redistributable (usually pre-installed on Windows 10+).

If the issue persists, run:

```powershell
.\python\python.exe -m pip install -r requirements-portable.txt --no-cache-dir
```

---

## Service URLs

| Service | URL |
|---|---|
| AiTao API | http://localhost:8200 |
| Health check | http://localhost:8200/api/health |
| Meilisearch | http://localhost:7700 |
| Ollama | http://localhost:11434 |
