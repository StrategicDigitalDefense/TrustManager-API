import sys
import os
import tempfile
import subprocess

# Ensure src/ and project root are in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from flask import Flask
from db.database import db
from models.certificates import Certificate

JKS_PATH = "static/trusted_certs.jks"
JKS_PASSWORD = "changeit"

def assemble_jks():
    # Remove existing JKS if present
    if os.path.exists(JKS_PATH):
        os.remove(JKS_PATH)

    # Use db.session for all DB operations
    trusted_certs = Certificate.query.filter_by(trusted=True).all()
    for idx, cert in enumerate(trusted_certs):
        alias = f"trusted_cert_{idx}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as pem_file:
            pem_file.write(cert.pem.encode())
            pem_file.flush()
            # Import PEM as trusted cert into JKS
            cmd = [
                "keytool",
                "-importcert",
                "-noprompt",
                "-trustcacerts",
                "-alias", alias,
                "-file", pem_file.name,
                "-keystore", JKS_PATH,
                "-storepass", JKS_PASSWORD
            ]
            subprocess.run(cmd, check=True)
            os.unlink(pem_file.name)
    print(f"JKS assembled at {JKS_PATH}")

if __name__ == "__main__":
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
    db.init_app(app)
    with app.app_context():
        assemble_jks()