import boto3
import mimetypes


class S3:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3 = boto3.resource('s3')

    def upload(self, local_file, bucket_file):
        bucket = self.s3.Bucket(self.bucket_name)
        mimetype, _ = mimetypes.guess_type(local_file)

        try:
            bucket.upload_file(local_file, bucket_file, ExtraArgs={'ContentType': mimetype})
            return {'info': bucket_file}
        except Exception as e:
            return {'error': str(e)}

    def presigned_url(self, bucket_file, expires_in):
        return self.s3.meta.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': self.bucket_name, 'Key': bucket_file},
            ExpiresIn=expires_in,
            HttpMethod='GET'
        )
