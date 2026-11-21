from argon2 import PasswordHasher
from argon2.exceptions import VerificationError,InvalidHashError
import hashlib

password_hasher=PasswordHasher()

def hash_password(password:str)->str:
    return password_hasher.hash(password)

def verify_password(password:str,password_hash:str)->bool:
    try:
        return password_hasher.verify(password_hash,password)
    except(VerificationError,InvalidHashError):
        return False

def hash_token(token:str)->str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()