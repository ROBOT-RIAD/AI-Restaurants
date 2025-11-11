import os
from cryptography.fernet import Fernet




SECRET_KEY = os.getenv('FERNET_KEY')
if not SECRET_KEY:
    raise ValueError("FERNET_KEY environment variable not set.")
fernet = Fernet(SECRET_KEY.encode())



def encrypt_text(text: str) -> str:
    if text is None:
        return None
    return fernet.encrypt(text.encode()).decode()

def decrypt_text(token: str) -> str:
    if token is None:
        return None
    return fernet.decrypt(token.encode()).decode()
