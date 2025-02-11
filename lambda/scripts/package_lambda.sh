#!/bin/bash

# Create a temporary directory for packaging
echo "Creating temporary directory..."
mkdir -p package

# Install requirements to the package directory
echo "Installing dependencies..."
pip install --target ./package -r requirements.txt

# Copy our Lambda function code
echo "Copying Lambda function code..."
cp main.py ./package/

# Create the ZIP file
echo "Creating deployment package..."
cd package
zip -r ../lambda_function.zip .
cd ..

# Move the ZIP file to the Terraform directory
echo "Moving deployment package to Terraform directory..."
mv lambda_function.zip ../../terraform/

# Clean up
echo "Cleaning up..."
rm -rf package

echo "Done! Lambda deployment package created at ../terraform/lambda_function.zip"