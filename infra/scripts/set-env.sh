#!/bin/bash
# This script sets environment variables for local development based on Bicep outputs
# Usage: ./scripts/set-env.sh

# Get outputs from azd env get-values (assumes azd deployment)
echo "Getting environment variables from azd..."

# Create .env file with Bicep outputs
cat > .env << EOF
# Environment variables
# Generated from Bicep deployment outputs

# Get azd env values once to avoid multiple calls
AZD_VALUES=$(azd env get-values --output json)

# ---- AOAI/LLM/Embedding Model Variables ----
AZURE_AI_PROJECT_ENDPOINT=$(echo "$AZD_VALUES" | jq -r '.AZURE_AI_PROJECT_ENDPOINT')
AZURE_AI_MODEL_DEPLOYMENT_NAME=$(echo "$AZD_VALUES" | jq -r '.AZURE_AI_MODEL_DEPLOYMENT_NAME')
EOF

echo ".env file created successfully with deployment outputs!"
echo "You can now use 'docker-compose up' to test your container locally."