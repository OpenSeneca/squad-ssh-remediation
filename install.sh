#!/bin/bash
# Squad SSH Remediation - Installation Script

set -e

echo "🔧 Installing Squad SSH Remediation..."

# Create symlink in ~/.local/bin
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -L "$INSTALL_DIR/squad-ssh-remediation" ]; then
    echo "Removing existing symlink..."
    rm "$INSTALL_DIR/squad-ssh-remediation"
fi

ln -s "$SCRIPT_DIR/main.py" "$INSTALL_DIR/squad-ssh-remediation"
chmod +x "$INSTALL_DIR/squad-ssh-remediation"

echo "✅ Installed to: $INSTALL_DIR/squad-ssh-remediation"
echo ""
echo "Usage:"
echo "  squad-ssh-remediation check    # Run full diagnostics"
echo "  squad-ssh-remediation status   # Print status summary"
echo "  squad-ssh-remediation checklist # Generate checklist"
echo "  squad-ssh-remediation export   # Export state as JSON"