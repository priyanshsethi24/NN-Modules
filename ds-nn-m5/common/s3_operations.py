import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

class S3Operations:
    def __init__(self, bucket_name='eqc-gito'):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('aws_access_key_id'),
            aws_secret_access_key=os.getenv('aws_secret_access_key'),
            region_name=os.getenv('aws_region')
        )
        self.bucket_name = bucket_name

    def download_directory(self, prefix: str, local_dir: str):
        """Download all files from a directory in S3"""
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        try:
            # List all objects with the given prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                for obj in page.get('Contents', []):
                    # Get the file path
                    key = obj['Key']
                    if key.lower().endswith(('.docx', '.pdf')):  # Only download documents
                        local_file = os.path.join(local_dir, os.path.basename(key))
                        print(f"Downloading: {key}")
                        
                        # Download the file
                        self.s3_client.download_file(
                            self.bucket_name,
                            key,
                            local_file
                        )
                        print(f"Downloaded to: {local_file}")
        except ClientError as e:
            raise Exception(f"Failed to download files from S3: {str(e)}")

    async def download_file(self, s3_path: str, local_path: str):
        try:
            # Parse s3 path (s3://bucket-name/key)
            key = '/'.join(s3_path.split('/')[3:])  # Skip s3:// and bucket name
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download the file
            self.s3_client.download_file(
                self.bucket_name,
                key,
                local_path
            )
            return local_path
        except ClientError as e:
            raise Exception(f"S3 download failed: {str(e)}")