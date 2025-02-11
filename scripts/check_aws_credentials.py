import boto3
import sys
from botocore.exceptions import ClientError, CredentialRetrievalError

def check_aws_credentials():
    """Perform a detailed verification of AWS credentials and permissions."""
    try:
        # Get current AWS identity
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"\n🔍 AWS Identity:")
        print(f"Account ID: {identity['Account']}")
        print(f"User/Role ARN: {identity['Arn']}")
        
        # Check configured region
        session = boto3.session.Session()
        current_region = session.region_name
        print(f"\n🌎 Current Region: {current_region}")
        
        # Try to list S3 buckets in all regions
        s3 = boto3.client('s3')
        try:
            response = s3.list_buckets()
            buckets = response['Buckets']
            print(f"\n📦 S3 Buckets:")
            if not buckets:
                print("No buckets found. This could mean either:")
                print("- You have no buckets in your account")
                print("- Your IAM permissions don't allow listing buckets")
            else:
                for bucket in buckets:
                    try:
                        region = s3.get_bucket_location(Bucket=bucket['Name'])
                        region_name = region['LocationConstraint'] or 'us-east-1'
                        print(f"- {bucket['Name']} (region: {region_name})")
                    except ClientError as e:
                        print(f"- {bucket['Name']} (region: unable to determine - {str(e)})")
        except ClientError as e:
            print(f"❌ Error listing S3 buckets: {str(e)}")
        
        # Check Lambda permissions
        print("\n⚡ Lambda Permissions:")
        try:
            lambda_client = boto3.client('lambda')
            lambda_client.list_functions()
            print("✅ Can list Lambda functions")
        except ClientError as e:
            print(f"❌ Lambda access error: {str(e)}")
        
        # Check CloudWatch permissions
        print("\n📊 CloudWatch Permissions:")
        try:
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.list_metrics()
            print("✅ Can access CloudWatch metrics")
        except ClientError as e:
            print(f"❌ CloudWatch access error: {str(e)}")
            
        # Check IAM permissions
        print("\n👤 IAM Permissions:")
        try:
            iam = boto3.client('iam')
            iam.get_user()
            print("✅ Can access IAM information")
        except ClientError as e:
            print(f"❌ IAM access error: {str(e)}")
            
        return True
        
    except CredentialRetrievalError as e:
        print(f"❌ AWS Credentials not found or invalid: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔒 AWS Credentials Check")
    print("=" * 50)
    success = check_aws_credentials()
    print("\n" + "=" * 50)
    print(f"Overall status: {'✅ Valid' if success else '❌ Invalid'}")
    sys.exit(0 if success else 1)