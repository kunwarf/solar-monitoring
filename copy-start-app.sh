#!/bin/bash
# Bash script to copy start app files (for Linux/WSL)

SOURCE="start-from-code-9c314cf4-main/src"
DEST="webapp-react/src/apps/start/src"

echo "Copying files from $SOURCE to $DEST..."

if [ ! -d "$SOURCE" ]; then
    echo "ERROR: Source directory not found: $SOURCE"
    exit 1
fi

# Create destination directory if it doesn't exist
mkdir -p "$DEST"

# Copy all files recursively
cp -r "$SOURCE"/* "$DEST"/

echo "Copy complete. Verifying..."

# Verify key files
KEY_FILES=(
    "pages/Index.tsx"
    "pages/Devices.tsx"
    "components/ProtectedRoute.tsx"
)

for file in "${KEY_FILES[@]}"; do
    if [ -f "$DEST/$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file MISSING"
    fi
done

echo "Done!"

