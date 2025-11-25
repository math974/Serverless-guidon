#!/bin/bash
set -e

# Arguments
BUILD_DIR="$1"
SOURCE_DIR="$2"
SHARED_PATH="$3"

# Create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy service source
cp -r "$SOURCE_DIR"/* "$BUILD_DIR/"

# Copy shared folder
cp -r "$SHARED_PATH" "$BUILD_DIR/shared"

# Return JSON with build_dir path for terraform
echo "{\"build_dir\": \"$BUILD_DIR\"}"

