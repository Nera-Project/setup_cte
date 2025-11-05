#!/bin/bash
set -e

# ===[ CONFIGURATION ]===
VENV_DIR=".venv_cte"
MAIN_SCRIPT="cte_client.py"
REPO_INFO_URL="https://raw.githubusercontent.com/Nera-Project/enrolling_thales_cte/main/main_package.info"

echo "🔹 Checking Python environment..."
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 tidak ditemukan. Install dulu sebelum lanjut."
    exit 1
fi

echo "✅ Python3 ditemukan: $(python3 --version)"

# ===[ SETUP VIRTUAL ENVIRONMENT ]===
if [ ! -d "$VENV_DIR" ]; then
    echo "🧱 Virtual environment belum ada, membuat baru di $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "♻️ Virtual environment sudah ada di $VENV_DIR — menggunakan yang lama."
fi

echo "⚙️ Mengaktifkan virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ===[ INSTALL DEPENDENCIES ]===
echo "📦 Memeriksa dan menginstal dependensi..."
pip install --upgrade pip >/dev/null
pip install requests >/dev/null

# ===[ FETCH REPOSITORY URL INFO ]===
echo "🌐 Mengambil URL repository dari GitHub..."
REPO_URL=$(curl -sL "$REPO_INFO_URL" | grep -Eo 'https://[^ ]+' | head -n 1)

if [ -z "$REPO_URL" ]; then
    echo "❌ Gagal mendapatkan URL dari GitHub ($REPO_INFO_URL)"
    deactivate
    exit 1
fi

echo "✅ Repository URL ditemukan: $REPO_URL"
export CTE_REPO_URL="$REPO_URL"

# ===[ JALANKAN SCRIPT PYTHON UTAMA ]===
if [ -f "$MAIN_SCRIPT" ]; then
    echo "🚀 Menjalankan script CTE Client..."
    python3 "$MAIN_SCRIPT" --repo "$CTE_REPO_URL"
else
    echo "⚠️ File $MAIN_SCRIPT tidak ditemukan, pastikan ada di direktori saat ini."
fi

deactivate
echo "🏁 Selesai setup environment dan eksekusi script."
