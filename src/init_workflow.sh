#!/bin/bash

# Initialize Searchio! workflow with default searches
# This script should be run after installing the workflow

echo "Initializing Searchio! workflow with default searches..."

# Get the workflow directory
WORKFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the reload command with defaults
cd "$WORKFLOW_DIR"
./searchio reload --defaults

echo "✅ Workflow initialized successfully!"
echo "Default searches added:"
echo "  - Google (English) - keyword: g"
echo "  - Wikipedia (English) - keyword: w"
echo "  - YouTube (United States) - keyword: yt"
echo ""
echo "You can now use these keywords in Alfred to search!" 