#!/bin/bash
# Pulse deployment script for AdminVPS (192.109.206.42)
set -e

echo "=== 1. Checking git status & committing changes ==="
git add .
if ! git diff-index --quiet HEAD --; then
    COMMIT_MSG=${1:-"fix: automated update of Pulse platform"}
    git commit -m "$COMMIT_MSG"
    unset GITHUB_TOKEN
    git push origin main
    echo "[+] Local changes pushed to GitHub!"
else
    echo "[*] No uncommitted local changes."
fi

echo "=== 2. Deploying to AdminVPS (192.109.206.42) ==="
ssh root@192.109.206.42 << 'EOF'
set -e
cd /var/www/pulse
git fetch origin main
git reset --hard origin/main

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q

echo "=== [OK] Pulse deployment completed successfully! ==="
EOF
