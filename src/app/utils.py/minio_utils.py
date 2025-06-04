import io
from minio import Minio
from minio.error import S3Error

class MinioClient:
    def __init__(self, endpoint, access_key, secret_key, secure=False):
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
    def ensure_bucket_exists(self, bucket_name):
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
            
    def upload_file(self, bucket_name, object_name, file_path):
        self.ensure_bucket_exists(bucket_name)
        self.client.fput_object(bucket_name, object_name, file_path)
        return f"minio://{bucket_name}/{object_name}"
        
    def download_file(self, bucket_name, object_name, file_path):
        self.client.fget_object(bucket_name, object_name, file_path)
        
    def upload_bytes(self, bucket_name, object_name, data):
        self.ensure_bucket_exists(bucket_name)
        self.client.put_object(
            bucket_name, object_name, io.BytesIO(data), length=len(data)
        )
        return f"minio://{bucket_name}/{object_name}"
        
    def download_bytes(self, bucket_name, object_name):
        response = self.client.get_object(bucket_name, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
        
    def list_objects(self, bucket_name, prefix=None):
        return self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
        
    def remove_object(self, bucket_name, object_name):
        self.client.remove_object(bucket_name, object_name)