import bcrypt

password = "5678"

hashed = bcrypt.hashpw(
    password.encode(),
    bcrypt.gensalt(),
)

print(hashed.decode())