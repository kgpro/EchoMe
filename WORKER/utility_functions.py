from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from datetime import datetime
from django.utils import timezone
import filetype
import mimetypes
from mutagen import File as MutagenFile


class utility_functions :
    def detailed_time_difference(self, target_datetime: datetime, max_units: int = 3) -> str:
        now = timezone.now()  # always timezone-aware

        # Make sure target_datetime is also timezone-aware
        if timezone.is_naive(target_datetime):
            target_datetime = timezone.make_aware(target_datetime)

        diff = now - target_datetime if now >= target_datetime else target_datetime - now
        is_past = now >= target_datetime

        seconds = int(diff.total_seconds())
        time_units = [
            ('year', 60 * 60 * 24 * 365),
            ('month', 60 * 60 * 24 * 30),
            ('week', 60 * 60 * 24 * 7),
            ('day', 60 * 60 * 24),
            ('hour', 60 * 60),
            ('minute', 60),
            ('second', 1),
        ]

        results = []
        for name, unit_seconds in time_units:
            value = seconds // unit_seconds
            if value > 0:
                results.append(f"{value} {name}{'s' if value > 1 else ''}")
                seconds %= unit_seconds
            if len(results) == max_units:
                break

        if not results:
            return "just now"

        if len(results) == 1:
            output = results[0]
        else:
            output = ", ".join(results[:-1]) + f", and {results[-1]}"

        return f"{output} ago" if is_past else f"in {output}"

    def decrypt_aes256_cbc(self,encrypted_bytes: bytes, decryption_pass: str) -> bytes:
        """
        Decrypts file bytes using AES-256-CBC with PKCS7 padding

        Args:
            encrypted_bytes: Encrypted file content (bytes)
            decryption_pass: Password used for decryption (str)

        Returns:
            Decrypted file bytes

        Raises:
            ValueError: If decryption fails (wrong password or corrupted data)
        """
        try:
            # Encrypted data format: salt (16 bytes) + iv (16 bytes) + ciphertext
            salt = encrypted_bytes[:16]
            iv = encrypted_bytes[16:32]
            ciphertext = encrypted_bytes[32:]

            # Derive key using PBKDF2HMAC with SHA256
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(decryption_pass.encode())

            # Decrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()

            # Unpad
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()

            return data

        except Exception as e:
            raise ValueError("Decryption failed: possibly wrong password or corrupted data.") from e

    def get_file_type(self, decrypted_file):
        '''
        Determines the MIME type and file extension of the decrypted file.

        Args:
            decrypted_file: Decrypted file content (bytes)

        Returns:
            tuple: (MIME type, file extension)

        '''

        kind = filetype.guess(decrypted_file)

        if kind:
            mime_type = kind.mime
            ext = f".{kind.extension}"
        else:
            # Check if it's audio using mutagen
            try:
                from io import BytesIO
                audio = MutagenFile(BytesIO(decrypted_file))
                if audio:
                    if audio.mime[0] == 'audio/mpeg':
                        mime_type = 'audio/mpeg'
                        ext = '.mp3'
                    elif audio.mime[0] == 'audio/wav':
                        mime_type = 'audio/wav'
                        ext = '.wav'
                    else:
                        mime_type = audio.mime[0]
                        ext = mimetypes.guess_extension(mime_type) or '.bin'
                else:
                    # fallback: maybe text
                    try:
                        decrypted_file.decode('utf-8')
                        mime_type = 'text/plain'
                        ext = '.txt'
                    except UnicodeDecodeError:
                        mime_type = 'application/octet-stream'
                        ext = '.bin'
            except Exception as e:
                print("mutagen error:", e)
                mime_type = "application/octet-stream"
                ext = ".bin"

        return mime_type, ext

