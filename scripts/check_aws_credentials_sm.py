import boto3
import sys

def check_aws_credentials():
    """Verify AWS credentials and list available services."""
    try:
        # Try to create an S3 client
        s3 = boto3.client('s3')
        # List buckets to verify permissions
        response = s3.list_buckets()
        print("✅ AWS Credentials verified successfully!")
        print(f"Found {len(response['Buckets'])} S3 buckets")
        
        # Check Lambda permissions
        lambda_client = boto3.client('lambda')
        lambda_client.list_functions()
        print("✅ Lambda access verified")
        
        # Check CloudWatch permissions
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.list_metrics()
        print("✅ CloudWatch access verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying AWS credentials: {str(e)}")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_aws_credentials() else 1)