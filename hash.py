from werkzeug.security import generate_password_hash

password = input('Introduce la contraseña a hashear: ')
hash = generate_password_hash(password)
print('Hash generado:')
print(hash)

with open('hash_generado.txt', 'w') as f:
    f.write(hash)
print('El hash también se guardó en hash_generado.txt')

input('Presiona Enter para salir...')
