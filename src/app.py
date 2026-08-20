from flask import Flask, config # type: ignore
from db.database import db
from models.certificates import Certificate  # <-- Import your model here!
from models.truststores import Truststore, TruststoreCertificate
from routes.certificates import certificates_bp, configure_oidc
from waitress import serve # type: ignore
import hashlib
import os
import secrets
import requests # type: ignore


app = Flask(__name__)
with app.app_context():
    oidc_client_secret = os.environ.get('TRUSTMANAGER_OIDC_CLIENT_SECRET')
    session_material = (
        oidc_client_secret.encode('utf-8')
        if oidc_client_secret
        else secrets.token_bytes(32)
    )
    app.config['SESSION_KEY'] = hashlib.pbkdf2_hmac(
        'sha256', session_material, secrets.token_bytes(16), 600_000, dklen=32
    )
    app.config['SECRET_KEY'] = app.config['SESSION_KEY']

    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['TRUSTMANAGER_DATABASE_URL']
    except KeyError:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
    try:
        if os.environ['TRUSTMANAGER_REQUIRE_AUTH'].lower() in [
            'true', '1', 't', 'yes', 'y'
        ]:
            app.config['AUTH'] = True
        else:
            app.config['AUTH'] = False
    except KeyError:
        app.config['AUTH'] = False

    if app.config['AUTH']:
        try:
            app.config['OIDC_CLIENT_ID'] = os.environ['TRUSTMANAGER_OIDC_CLIENT_ID']
            app.config['OIDC_CLIENT_SECRET'] = os.environ['TRUSTMANAGER_OIDC_CLIENT_SECRET']
            app.config['OIDC_METADATA_URL'] = os.environ['TRUSTMANAGER_OIDC_METADATA_URL']
        except KeyError:
            app.config['AUTH'] = False  # Disable auth if OIDC config is missing

    if app.config['AUTH']:
        try:
            response = requests.get(app.config['OIDC_METADATA_URL'], timeout=10)
            response.raise_for_status()
            metadata = response.json()
            for setting in ('authorization_endpoint', 'token_endpoint', 'jwks_uri', 'issuer'):
                if setting in metadata:
                    app.config[f'OIDC_{setting.upper()}'] = metadata[setting]
            if not app.config.get('OIDC_AUTHORIZATION_ENDPOINT') or not app.config.get('OIDC_TOKEN_ENDPOINT'):
                raise ValueError('OIDC metadata is missing an authorization or token endpoint')
            app.config['OIDC_METADATA'] = metadata
        except (requests.RequestException, ValueError) as error:
            raise RuntimeError(f'Unable to load OIDC metadata: {error}') from error

    configure_oidc(app)
    db.init_app(app)  # <-- This is required

    with app.app_context():
        db.create_all()  # Optional: creates tables if not present

    app.register_blueprint(certificates_bp)



if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5100, debug=True)
    serve(app, host="0.0.0.0", port=5100)