#!/bin/bash
# Package Lambda function for deployment

set -e

# Navigate to function directory
cd "$(dirname "$0")"

# Create package directory
rm -rf package
mkdir -p package

# Copy function code
cp index.py package/

# Create zip file
cd package
zip -r ../contact_form_lambda.zip .
cd ..

# Move zip to terraform directory
mv contact_form_lambda.zip ../../terraform/

echo "Lambda function packaged successfully!"
