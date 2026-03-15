# coding=utf-8
import hashlib


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
