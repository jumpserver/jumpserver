import os
import csv
import pyzipper


def create_csv_file(filename, headers, rows, ):
    with open(filename, 'w', encoding='utf-8-sig')as f:
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
