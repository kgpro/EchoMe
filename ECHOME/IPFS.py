import boto3
from botocore.client import Config
from django.conf import settings
import os

def get_timestamp():
    """
    Generates a timestamped filename for uploads.
    :return: Formatted filename string
    """
    from datetime import datetime
    timestamp = str(datetime.now().strftime("%Y%m%d%H%M%S"))
    return timestamp


class FilebaseIPFS:

    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url='https://s3.filebase.com',
            aws_access_key_id=settings.FILEBASE_KEY,
            aws_secret_access_key=settings.FILEBASE_SECRET,
            config=Config(signature_version='s3v4')
        )
        self.bucket = settings.BUCKET_NAME

    def upload_and_get_cid(self, file_obj, object_name=None):
        """
        Uploads a file-like object (or path) to Filebase IPFS and returns its CID.

        :param file_obj: Either a path to a file OR an InMemoryUploadedFile (from request.FILES)
        :param object_name: Optional name to store in bucket
        :return: CID string if successful, else None
        """
        try:
            if isinstance(file_obj, str):  # It's a file path
                if not object_name:
                    object_name = get_timestamp() #time stamp as filename
                self.client.upload_file(
                    file_obj,
                    self.bucket,
                    object_name,
                    ExtraArgs={'Metadata': {'ipfs': 'true'}}
                )
            else:
                if not object_name:
                    object_name = get_timestamp()
                self.client.upload_fileobj(
                    Fileobj=file_obj,
                    Bucket=self.bucket,
                    Key=object_name,
                    ExtraArgs={'Metadata': {'ipfs': 'true'}}
                )

            # Wait a moment and retrieve CID
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=object_name
            )
            cid = response['Metadata'].get('cid')

            if not cid:
                print(" CID not available in metadata.")
                return None

            return cid

        except Exception as e:
            print(f" Upload failed: {str(e)}")
            return None

    def get_file_by_cid(self, cid, save_path=None):
        """
        Downloads a file using its IPFS CID from Filebase.
        If save_path is a directory or None, handles accordingly.

        :param cid: IPFS content identifier
        :param save_path: Full file path or directory or None
        :return: dict with 'bytes', 'path' (optional), 'mime_type'
        """
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket)
            print(" Searching for CID in bucket...")
            object_key = None
            for page in page_iterator:
                for obj in page.get('Contents', []):
                    metadata = self.client.head_object(
                        Bucket=self.bucket,
                        Key=obj['Key']
                    )['Metadata']
                    if metadata.get('cid') == cid:
                        object_key = obj['Key']
                        break
                if object_key:
                    break

            if not object_key:
                print(" CID not found in bucket.")
                return None

            # Get raw file content
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=object_key
            )
            file_bytes = response['Body'].read()
            print("got file bytes")
            # Detect file type
            # mime = magic.Magic(mime=True)
            # mime_type = mime.from_buffer(file_bytes)
            # ext = mimetypes.guess_extension(mime_type) or '.bin'
            # print("got file extension")
            # Handle save logic
            save_result = None
            if save_path:
                if os.path.isdir(save_path):
                    filename = f"{cid}{ext}"
                    save_path = os.path.join(save_path, filename)

                # Ensure directory exists
                Path(os.path.dirname(save_path)).mkdir(parents=True, exist_ok=True)

                with open(save_path, 'wb') as f:
                    f.write(file_bytes)

                #  delete from Filebase
                self.client.delete_object(Bucket=self.bucket, Key=object_key)

                save_result = save_path
                print(f" File saved to: {save_result}")

            return {
                'bytes': file_bytes,
                'path': save_result,
            }

        except Exception as e:
            print(f" Retrieval failed: {str(e)}")
            return None


    def delete_file_by_cid(self, cid):
        """
        Deletes a file from Filebase using its IPFS CID.

        :param cid: IPFS content identifier to delete
        :return: True if deleted successfully, False otherwise
        """
        try:
            # First find the object key matching the CID
            paginator = self.client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket)

            object_key = None
            for page in page_iterator:
                for obj in page.get('Contents', []):
                    metadata = self.client.head_object(
                        Bucket=self.bucket,
                        Key=obj['Key']
                    )['Metadata']
                    if metadata.get('cid') == cid:
                        object_key = obj['Key']
                        break
                if object_key:
                    break

            if not object_key:
                print(f" CID {cid} not found in bucket.")
                return False

            # Delete the object
            self.client.delete_object(
                Bucket=self.bucket,
                Key=object_key
            )

            print(f" Successfully deleted file with CID: {cid}")
            return True

        except Exception as e:
            print(f"Deletion failed for CID {cid}: {str(e)}")
            return False



