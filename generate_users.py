import pandas as pd
import random
import string

def generate_password(length=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

users = [f"user{i}" for i in range(1, 11)]
passwords = [generate_password() for _ in range(10)]

df = pd.DataFrame({
    'username': users,
    'password': passwords
})

df.to_excel('users.xlsx', index=False)