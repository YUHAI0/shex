#!/bin/bash
set -e

echo "Starting Shex installation..."

# Navigate to project root if running from scripts directory
if [ -f "../pyproject.toml" ]; then
    cd ..
elif [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run this script from the project root or scripts directory."
    exit 1
fi

# Check for Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

echo "Found Python: $($PYTHON --version)"

# Update source code if git repo
if [ -d ".git" ]; then
    echo "Updating source code from git..."
    git pull || echo "Warning: Failed to update source code."
fi

# Install/Upgrade Shex
echo "Installing/Updating Shex..."
$PYTHON -m pip install --upgrade pip setuptools wheel

# Try installing. If permission denied, suggest using sudo or --user
if ! $PYTHON -m pip install --upgrade .; then
    echo "Installation failed. Trying with --user..."
    $PYTHON -m pip install --upgrade --user .
fi

# Verify installation
if command -v shex &> /dev/null; then
    echo -e "\033[0;32mShex installed successfully!\033[0m"
    echo "You can now run 'shex' from the command line."
    shex --version
else
    echo -e "\033[0;33mWarning: Shex installed but 'shex' command not found in PATH.\033[0m"
    
    # Check user local bin
    USER_BASE=$($PYTHON -m site --user-base)
    USER_BIN="$USER_BASE/bin"
    
    if [ -f "$USER_BIN/shex" ]; then
        echo "Found executable at: $USER_BIN/shex"
        
        # Detect shell config
        SHELL_CFG=""
        case "$SHELL" in
        */zsh)
            SHELL_CFG="$HOME/.zshrc"
            ;;
        */bash)
            if [ -f "$HOME/.bashrc" ]; then
                SHELL_CFG="$HOME/.bashrc"
            elif [ -f "$HOME/.bash_profile" ]; then
                SHELL_CFG="$HOME/.bash_profile"
            fi
            ;;
        *)
            if [ -f "$HOME/.profile" ]; then
                SHELL_CFG="$HOME/.profile"
            fi
            ;;
        esac

        if [ -n "$SHELL_CFG" ]; then
            if ! grep -q "$USER_BIN" "$SHELL_CFG"; then
                echo "Adding '$USER_BIN' to $SHELL_CFG..."
                echo "" >> "$SHELL_CFG"
                echo "# Added by Shex installer" >> "$SHELL_CFG"
                echo "export PATH=\"\$PATH:$USER_BIN\"" >> "$SHELL_CFG"
                echo -e "\033[0;32mAdded to PATH in $SHELL_CFG.\033[0m"
                echo "Please restart your shell or run 'source $SHELL_CFG' to use 'shex'."
            else
                 echo "'$USER_BIN' is already in $SHELL_CFG"
            fi
        else
            echo "Could not detect shell configuration file. Please add '$USER_BIN' to your PATH manually."
        fi
    fi
fi
