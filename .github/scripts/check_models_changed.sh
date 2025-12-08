#!/bin/bash

# This script checks if any models lists were updated in YAML files

# For Devs: Explanation of how the gross yaml check below works:
  # 1. Print the git diff between the before and after sha (include 1000 lines of context between changes (overkill, should always get the whole file))
  # 2. If we find the models key, start printing lines
  # 3. If we find a new top level key, stop printing
  # 4. Check the lines that were printed for additions or deletions (+/-)
  # 5. If there are any additions or deletions, set MODELS_CHANGED to true

# Arguments:
#   $1: List of changed files
#   $2: Before SHA
#   $3: After SHA

CHANGED_FILES="$1"
BEFORE_SHA="$2"
AFTER_SHA="$3"

MODELS_CHANGED=false

while read file; do
  if git diff -U1000 "$BEFORE_SHA" "$AFTER_SHA" "$file" | awk '/^[ +-]?models:/{p=1} /^[ +-]?[a-zA-Z_-]+:/{if ($0 !~ /^[ +-]?models:/ && NF>0) p=0} p' | grep -E "^[+-]" > /dev/null; then
    MODELS_CHANGED=true
    break
  fi
done < <(echo "$CHANGED_FILES" | grep -E "\.ya?ml$")

echo "$MODELS_CHANGED"
