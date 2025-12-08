#!/bin/bash
# Setup PAL MCP Server for multi-model consensus in CI
set -e

echo "Installing PAL MCP Server..."
npm install -g @anthropic/pal-mcp-server

echo "PAL MCP Server installed successfully"
echo "Available tools: consensus, codereview, precommit, thinkdeep, clink"
