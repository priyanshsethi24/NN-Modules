import os
import boto3
from common.logs import logger
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
aws_region_name = os.getenv('aws_region')

class S3Helper:
    def __init__(self, s3_bucket_name) -> None:
        '''
        Initializes the S3Helper object.
        '''
        self.bucket_name = s3_bucket_name
        self.s3_client = boto3.client(
            's3',
            region_name=aws_region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        self.logger = logger

    def upload_file_to_s3(self, file_name: str, object_name: str) -> None:
        '''
        Uploads a file to S3 bucket.
        '''
        try:
            self.s3_client.upload_file(file_name, self.bucket_name, object_name)
            self.logger.info(f"File '{file_name}' uploaded to S3 bucket '{self.bucket_name}' as '{object_name}'.")
        except Exception as e:
            self.logger.exception(f"Exception in upload_file_to_s3(): File - '{file_name}', S3 bucket - '{self.bucket_name}', object_name - '{object_name}'")
            raise e

    def download_file_from_s3(self, object_name: str, file_name: str) -> None:
        '''
        Downloads a file from S3 bucket.
        '''
        try:
            self.logger.info(f"Downloading file from S3: Bucket - '{self.bucket_name}', Object - '{object_name}', Local - '{file_name}'")
            self.s3_client.download_file(self.bucket_name, object_name, file_name)
            self.logger.info(f"File '{object_name}' downloaded from S3 bucket '{self.bucket_name}' to '{file_name}'.")
        except ClientError as e:
            self.logger.exception(f"ClientError in download_file_from_s3(): File - '{object_name}', S3 bucket - '{self.bucket_name}', to - '{file_name}'")
            raise e
        except Exception as e:
            self.logger.exception(f"Exception in download_file_from_s3(): File - '{object_name}', S3 bucket - '{self.bucket_name}', to - '{file_name}'")
            raise e

    def upload_directory(self, dir_name: str, prefix: str = "") -> None:
        '''
        Uploads a directory to S3 bucket.
        '''
        try:
            for root, dirs, files in os.walk(dir_name):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file_path, dir_name)
                    s3_object_name = os.path.join(prefix, relative_path)
                    self.upload_file_to_s3(local_file_path, s3_object_name)
        except Exception as e:
            self.logger.exception(f"Exception in upload_directory(): inp_dir_name - {dir_name}")
            raise e

    def download_directory(self, s3_prefix: str, local_dir: str) -> None:
        '''
        Downloads a directory from S3 bucket to local directory.
        Args:
            s3_prefix (str): The S3 prefix (folder path) to download from
            local_dir (str): The local directory path to download to
        '''
        try:
            # Create the local directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)
            
            # List all objects in the S3 prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            operation_parameters = {'Bucket': self.bucket_name, 'Prefix': s3_prefix}
            page_iterator = paginator.paginate(**operation_parameters)
            
            # Track if we found any files
            files_found = False
            
            for page in page_iterator:
                if 'Contents' not in page:
                    continue
                    
                files_found = True
                for item in page['Contents']:
                    key = item['Key']
                    if not key.endswith('/'):  # Skip S3 "directory" objects
                        # Calculate the relative path
                        rel_path = key[len(s3_prefix):].lstrip('/')
                        local_file_path = os.path.join(local_dir, rel_path)
                        
                        # Create the directory structure if it doesn't exist
                        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                        
                        # Download the file
                        self.logger.info(f"Downloading {key} to {local_file_path}")
                        self.s3_client.download_file(self.bucket_name, key, local_file_path)
            
            if not files_found:
                self.logger.warning(f"No files found in S3 bucket '{self.bucket_name}' with prefix '{s3_prefix}'")
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                self.logger.error(f"The S3 prefix '{s3_prefix}' does not exist in bucket '{self.bucket_name}'")
            else:
                self.logger.exception(f"ClientError in download_directory(): {str(e)}")
            raise e
        except Exception as e:
            self.logger.exception(f"Exception in download_directory(): {str(e)}")
            raise e 