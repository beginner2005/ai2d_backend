import boto3
from app.core.config import settings

class R2Storage:
    def __init__(self):
        self.s3_client = boto3.client(
            service_name='s3',
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            region_name="auto", 
        )
        self.bucket_name = settings.R2_BUCKET_NAME

    def generate_presigned_url(self, file_name: str, expiration=3600):
        """
        Tạo link ảnh có hạn sử dụng (mặc định 1 tiếng)
        """
        try:
            # Nếu file name trong DB chưa có folder, thêm vào (tùy cấu trúc bạn upload)
            object_name = f"ai2d/raw/{file_name}" 
            
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
            return response
        except Exception as e:
            print(f"- Error generating URL: {e}")
            return None

# Tạo instance dùng chung
storage_client = R2Storage()