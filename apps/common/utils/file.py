import csv
import hashlib
import os

import pyzipper
import requests
from django.conf import settings


def create_csv_file(filename, headers, rows, ):
    with open(filename, 'w', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def encrypt_and_compress_zip_file(filename, secret_password, encrypted_filenames):
    with pyzipper.AESZipFile(
            filename, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES
    ) as zf:
        zf.setpassword(secret_password)
        for encrypted_filename in encrypted_filenames:
            with open(encrypted_filename, 'rb') as f:
                zf.writestr(os.path.basename(encrypted_filename), f.read())


def download_file(src, path):
    with requests.get(src, stream=True) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def save_content_to_temp_path(content, file_mode=0o400):
    if not content:
        return

    project_dir = settings.PROJECT_DIR
    tmp_dir = os.path.join(project_dir, 'tmp')
    filename = '.' + hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
    filepath = os.path.join(tmp_dir, filename)
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write(content)
        os.chmod(filepath, file_mode)
    return filepath
