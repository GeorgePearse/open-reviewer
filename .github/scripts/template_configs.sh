#!/bin/bash

set -eo pipefail

CURRENT_DATE=$1
FLEET=$2
CLIENT=$3
GITHUB_SHA=$4

# Detect if running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_CMD="sed -i .bak"
else
    SED_CMD="sed -i"
fi



SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"/../../controlunit

$SED_CMD "s/\(version:.*\)/version: $CURRENT_DATE-$FLEET-$CLIENT/" fleets/"$FLEET"/balena.yml
echo "Balena configuration:"
cat fleets/"$FLEET"/balena.yml

$SED_CMD "s/{GIT_SHA}/$GITHUB_SHA/g" fleets/"$FLEET"/docker-compose.yml
$SED_CMD "s/{CLIENT}/$CLIENT/g" fleets/"$FLEET"/docker-compose.yml
echo "Docker compose:"
cat fleets/"$FLEET"/docker-compose.yml
