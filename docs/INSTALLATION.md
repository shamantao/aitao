# AiTao Installation

This guide is for non-technical users. Follow the steps exactly.

---

## Before you start

You only need one thing: **Docker Desktop**.

Install Docker Desktop for your system:
- macOS (Apple Silicon): https://docs.docker.com/desktop/install/mac-install/
- Windows 10/11: https://docs.docker.com/desktop/install/windows-install/
- Linux: https://docs.docker.com/desktop/install/linux-install/

After installing, restart your computer and open Docker Desktop before continuing.

---

## Installation in 3 steps

### Step 1 - Unzip the archive

1. Download the AiTao archive for your system:
   - aitao-macos-arm64.zip (macOS Apple Silicon)
   - aitao-windows-x64.zip (Windows 10+)
   - aitao-linux-x64.zip (Linux)

2. Unzip the archive into any folder.

You should see files like:
```
install-aitao.sh      (macOS/Linux)
install-aitao.bat     (Windows)
docker-compose.yml
.env.template
README.md
```

---

### Step 2 - Run the install script

The script will:
- Check Docker Desktop is installed
- Create configuration folders
- Download and start all services

macOS/Linux:
```bash
chmod +x install-aitao.sh
./install-aitao.sh
```

Windows:
1. Open PowerShell or Command Prompt
2. Go to the folder you unzipped
3. Run: install-aitao.bat

The first install can take 3-5 minutes (it downloads large images).

---

### Step 3 - Open AiTao

When the install finishes, open:

http://localhost:3000

You can now use AiTao.

---

## Common problems

### "Docker is not installed"

Fix:
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install it
3. Restart your computer
4. Open Docker Desktop
5. Run the install script again

---

### "Docker is not running"

Fix:
1. Open Docker Desktop
2. Wait until it is fully started
3. Run the install script again

---

### "Port 8200 or 3000 is already in use"

Meaning: another app is using the same port.

Fix:
1. Close the other app
2. Restart AiTao

Restart AiTao:
```bash
docker-compose restart
```

---

### "The first connection is slow"

This is normal. AiTao downloads AI models the first time.
Please wait a few minutes.

---

## Useful commands (optional)

```bash
# See logs
docker-compose logs -f

# Stop AiTao
docker-compose down

# Restart AiTao
docker-compose restart

# Uninstall completely
./uninstall-aitao.sh        # macOS/Linux
uninstall-aitao.bat         # Windows
```

---

## Need help?

1. Make sure Docker Desktop is running
2. Try: docker-compose down then docker-compose up -d
3. Check your internet connection

---

Enjoy AiTao.
