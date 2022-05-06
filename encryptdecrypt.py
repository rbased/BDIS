import cryptography
from cryptography.fernet import Fernet
import pandas as pd
from io import BytesIO

def encrypt(filepath, key):
    fernet = Fernet(key)
    with open(filepath, 'rb') as file:
        original = file.read()

    encrypted = fernet.encrypt(original)
    with open(filepath, 'wb') as encrypted_file:
        encrypted_file.write(encrypted)

def decrypt(filepath, key):
    fernet = Fernet(key)

    # opening the encrypted file
    with open(filepath, 'rb') as enc_file:
        encrypted = enc_file.read()

    # decrypting the file
    decrypted = fernet.decrypt(encrypted)
    df = pd.read_excel(BytesIO(decrypted), engine = 'openpyxl')
    return df
