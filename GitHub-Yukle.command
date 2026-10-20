#!/bin/bash
# LegalDesk Pro - GitHub repository creator/uploader (macOS)
# Creates https://github.com/muratpalak/LegalDesk-Pro as a public repository.
# Does not force-push, and refuses unexpected authenticated accounts/remotes.
set -euo pipefail

cd "$(dirname "$0")"
OWNER="muratpalak"
NAME="LegalDesk-Pro"
REPO="$OWNER/$NAME"
EXPECTED_REMOTE="https://github.com/$REPO.git"

echo ""
echo "==============================================="
echo "  LegalDesk Pro - GitHub'a Guvenli Yukleme"
echo "==============================================="
echo "Hedef: https://github.com/$REPO"
echo ""

if ! command -v git >/dev/null 2>&1; then
  echo "HATA: Git bulunamadi. Once Xcode Command Line Tools kurun: xcode-select --install"
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "HATA: GitHub CLI (gh) bulunamadi. Mac Terminal: brew install gh"
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub oturumu aciliyor (tarayici girisi gerekli)..."
  gh auth login --hostname github.com --git-protocol https --web
fi

ACTUAL_OWNER="$(gh api user --jq .login)"
if [[ "$ACTUAL_OWNER" != "$OWNER" ]]; then
  echo "HATA: GitHub hesabiniz $ACTUAL_OWNER, beklenen: $OWNER"
  echo "Hesabi duzeltmek icin: gh auth switch"
  exit 1
fi

gh auth setup-git

if [[ ! -d .git ]]; then
  git init -b main
fi

BRANCH="$(git branch --show-current)"
if [[ -n "$BRANCH" && "$BRANCH" != "main" ]]; then
  echo "HATA: Dizin baska bir Git dalinda ($BRANCH). Yanlis projeyi gondermemek icin durduruldu."
  exit 1
fi

# Refuse to stage stored legal data or secrets even if ignore rules are edited.
git add -A
if git diff --cached --name-only | grep -E '(^app/data/|^\.env($|\.)|(^|/)(secrets|private|backups)/|\.(sqlite3?|db|pem|p12|pfx|key)$)' >/dev/null; then
  echo "HATA: Ozel veri veya gizli dosya Git'e eklenmis. Yukleme iptal edildi."
  exit 1
fi

if ! git diff --cached --quiet; then
  if ! git var GIT_AUTHOR_IDENT >/dev/null 2>&1; then
    echo "Git yazar adi/e-postasi tanimli degil."
    read -r -p "Git yazar adi: " AUTHOR_NAME
    read -r -p "Git e-posta adresi: " AUTHOR_EMAIL
    git config user.name "$AUTHOR_NAME"
    git config user.email "$AUTHOR_EMAIL"
  fi
  git commit -m "Release LegalDesk Pro v1.0 - local-first law firm dashboard"
fi

if git remote get-url origin >/dev/null 2>&1; then
  EXISTING_REMOTE="$(git remote get-url origin)"
  if [[ "$EXISTING_REMOTE" != "$EXPECTED_REMOTE" && "$EXISTING_REMOTE" != "git@github.com:$REPO.git" ]]; then
    echo "HATA: origin baska depoya bagli: $EXISTING_REMOTE"
    exit 1
  fi
fi

if gh repo view "$REPO" --json name >/dev/null 2>&1; then
  echo "GitHub deposu zaten var; mevcut depoya guvenli push yapiliyor."
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$EXPECTED_REMOTE"
  fi
  git push -u origin main
else
  echo "Yeni herkese acik GitHub deposu olusturuluyor ve dosyalar gonderiliyor..."
  gh repo create "$REPO" --public --description "Local-first law office management portfolio demo (FastAPI, SQLite, JavaScript)" --source=. --remote=origin --push
fi

echo ""
echo "BASARILI: https://github.com/$REPO"
echo "Kontrol icin: gh repo view $REPO --web"
