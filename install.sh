#!/bin/sh
# Parsemux installer — curl -fsSL https://raw.githubusercontent.com/vericontext/parsemux/main/install.sh | sh
set -e

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

info()  { printf "${GREEN}[parsemux]${RESET} %s\n" "$1"; }
warn()  { printf "${YELLOW}[parsemux]${RESET} %s\n" "$1"; }
error() { printf "${RED}[parsemux]${RESET} %s\n" "$1"; exit 1; }

# --- Check Python ---
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3.11+ is required. Install from https://python.org or via pyenv/uv."
fi
info "Found $PYTHON ($ver)"

# --- Check pip / uv ---
INSTALLER=""
if command -v uv >/dev/null 2>&1; then
    INSTALLER="uv pip install"
    info "Using uv for installation"
elif "$PYTHON" -m pip --version >/dev/null 2>&1; then
    INSTALLER="$PYTHON -m pip install"
    info "Using pip for installation"
else
    error "pip or uv is required. Install with: $PYTHON -m ensurepip --upgrade"
fi

# --- Install parsemux ---
EXTRAS="pymupdf,kreuzberg,cli"

info "Installing parsemux[${EXTRAS}]..."
$INSTALLER "parsemux[${EXTRAS}]" || error "Installation failed"

# --- Verify ---
if command -v parsemux >/dev/null 2>&1; then
    info "$(parsemux version)"
    info "Installation complete!"
    echo ""
    printf "${BOLD}Quick start:${RESET}\n"
    echo "  parsemux parse document.pdf              # Parse a document"
    echo "  parsemux parse document.pdf --format json # JSON output"
    echo "  parsemux serve                            # Start API server"
    echo "  parsemux list-parsers                     # Show available parsers"
    echo "  parsemux schema                           # Show schema (for AI agents)"
    echo ""
    printf "${BOLD}Optional — add VLM image description:${RESET}\n"
    echo "  pip install 'parsemux[vlm]'"
    echo "  parsemux parse doc.pdf --extract-images --describe-images --vlm-key sk-..."
    echo ""
    printf "${BOLD}Optional — system dependencies for OCR:${RESET}\n"
    case "$(uname -s)" in
        Darwin*) echo "  brew install tesseract libmagic" ;;
        Linux*)  echo "  sudo apt-get install -y tesseract-ocr libmagic1" ;;
    esac
else
    warn "parsemux installed but not found in PATH."
    warn "You may need to add your Python bin directory to PATH."
    warn "Try: $PYTHON -m parsemux.cli.main version"
fi
