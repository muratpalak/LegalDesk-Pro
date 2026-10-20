#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 bulunamadı. https://www.python.org/downloads/"
  read -r -p "Kapatmak için Enter: "
  exit 1
fi
if [ ! -f .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt || { echo "Paket kurulumu başarısız."; exit 1; }
echo "LegalDesk Pro açılıyor: http://127.0.0.1:8765"
(sleep 2; open http://127.0.0.1:8765) &
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
