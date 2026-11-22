#!/usr/bin/env bash
# Start the Next.js frontend
set -e
cd "$(dirname "$0")/frontend"
npm run dev
