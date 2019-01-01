"""dummy module replacement for the keychain module."""

_PASSWORDS = {}


def get_password(service, account):
    return _PASSWORDS[(service, account)]

def set_password(service, account, password):
    _PASSWORDS[(service, account)] = password

def delete_password(service, account):
    del _PASSWORDS[(service, account)]

def reset_keychain():
    for key in _PASSWORDS.keys():
        del _PASSWORDS[key]

def get_services():
    return [k for k in _PASSWORDS]