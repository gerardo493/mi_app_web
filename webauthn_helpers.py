import os
from flask import session
from py_webauthn import (WebAuthnUser, WebAuthnRegistrationOptions, WebAuthnAssertionOptions, WebAuthnCredential, WebAuthnRegistrationResponse, WebAuthnAssertionResponse)

RP_ID = os.environ.get('WEBAUTHN_RP_ID', 'localhost')
RP_NAME = os.environ.get('WEBAUTHN_RP_NAME', 'Sistema de Facturación')
ORIGIN = os.environ.get('WEBAUTHN_ORIGIN', 'http://localhost:5000')


def get_webauthn_user(user):
    # user: objeto de usuario de la base de datos
    return WebAuthnUser(
        user_id=str(user.id),
        username=user.username,
        display_name=user.username,
        icon_url=None,
        credential_id=user.credential_id,
        public_key=user.public_key,
        sign_count=user.sign_count,
        rp_id=RP_ID
    )

def generate_registration_options(user):
    return WebAuthnRegistrationOptions(
        rp_name=RP_NAME,
        rp_id=RP_ID,
        user_id=str(user.id),
        username=user.username,
        display_name=user.username,
        challenge=None,
        attestation='none',
        authenticator_selection={'userVerification': 'preferred'},
        timeout=60000
    )

def generate_assertion_options(user):
    return WebAuthnAssertionOptions(
        rp_id=RP_ID,
        challenge=None,
        allow_credentials=[user.credential_id] if user.credential_id else [],
        user_verification='preferred',
        timeout=60000
    ) 