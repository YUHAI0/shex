#!/bin/bash
set -e

echo "Starting Shex installation..."

# Determine installation mode (Local or Remote)
IS_LOCAL=false
if [ -f "../pyproject.toml" ]; then
    cd ..
    IS_LOCAL=true
elif [ -f "pyproject.toml" ]; then
    IS_LOCAL=true
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

add_user_bin_to_path() {
    local user_bin="$1"
    local shell_cfg=""
    local platform

    platform="$(uname -s)"

    case "$SHELL" in
    */zsh)
        shell_cfg="$HOME/.zshrc"
        ;;
    */bash)
        case "$platform" in
        Darwin)
            shell_cfg="$HOME/.bash_profile"
            ;;
        *)
            shell_cfg="$HOME/.bashrc"
            ;;
        esac
        ;;
    *)
        echo "Could not detect bash or zsh. Please add '$user_bin' to your PATH manually."
        return
        ;;
    esac

    if [ ! -f "$shell_cfg" ]; then
        touch "$shell_cfg"
    fi

    if grep -Fq "$user_bin" "$shell_cfg"; then
        echo "'$user_bin' is already in $shell_cfg"
    else
        echo "Adding '$user_bin' to $shell_cfg..."
        {
            echo ""
            echo "# Added by Shex installer"
            echo "export PATH=\"\$PATH:$user_bin\""
        } >> "$shell_cfg"
        echo -e "\033[0;32mAdded to PATH in $shell_cfg.\033[0m"
    fi

    echo "Please run 'source $shell_cfg' to use 'shex' in this shell."
}

if [ "$IS_LOCAL" = true ]; then
    # Update source code if git repo
    if [ -d ".git" ]; then
        echo "Updating source code from git..."
        git pull || echo "Warning: Failed to update source code."
    fi

    # Install/Upgrade Shex from local source
    echo "Installing/Updating Shex from local source..."
    $PYTHON -m pip install --upgrade pip setuptools wheel

    # Try installing. If permission denied, suggest using sudo or --user
    if ! $PYTHON -m pip install --upgrade .; then
        echo "Installation failed. Trying with --user..."
        $PYTHON -m pip install --upgrade --user .
    fi
else
    # Remote installation from GitHub
    echo "Installing/Updating Shex from GitHub..."
    $PYTHON -m pip install --upgrade pip setuptools wheel

    # Try installing. If permission denied, suggest using sudo or --user
    if ! $PYTHON -m pip install --upgrade https://github.com/YUHAI0/shex/archive/master.zip; then
        echo "Installation failed. Trying with --user..."
        $PYTHON -m pip install --upgrade --user https://github.com/YUHAI0/shex/archive/master.zip
    fi
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
        add_user_bin_to_path "$USER_BIN"
    fi
fi
