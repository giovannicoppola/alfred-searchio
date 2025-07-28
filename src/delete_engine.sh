#!/bin/bash

# Simple script to delete a search engine and reload
# Usage: ./delete_engine.sh <search_uid>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <search_uid>"
    echo "Example: $0 google-en"
    exit 1
fi

search_uid="$1"

echo "Deleting search engine: $search_uid"

# Call the delete command
./searchio delete "$search_uid"

# Reload the workflow
echo "Reloading workflow..."
./searchio reload

echo "Done. Search engine '$search_uid' has been deleted and workflow reloaded."
