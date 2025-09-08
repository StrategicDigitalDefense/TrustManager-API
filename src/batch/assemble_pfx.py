import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from flask import Flask
from db.database import db
from models.certificates import Certificate
import subprocess
import tempfile

PFX_PATH = "static/trusted_certs.pfx"
PFX_PASSWORD = "changeit"

def assemble_pfx():
    # Remove existing PFX if present
    if os.path.exists(PFX_PATH):
        os.remove(PFX_PATH)

    trusted_certs = Certificate.query.filter_by(trusted=True).all()
    if not trusted_certs:
        print("No trusted certificates found.")
        return

    # Write all trusted certs to a single PEM file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as pem_file:
        for cert in trusted_certs:
            pem_file.write(cert.pem.encode() + b"\n")
        pem_file.flush()

        # Use OpenSSL to create PKCS#12 (PFX) bundle
        cmd = [
            "openssl", "pkcs12",
            "-export",
            "-nokeys",
            "-out", PFX_PATH,
            "-in", pem_file.name,
            "-name", "trusted_certs",
            "-passout", f"pass:{PFX_PASSWORD}"
        ]
        subprocess.run(cmd, check=True)
        os.unlink(pem_file.name)

    print(f"PFX assembled at {PFX_PATH}")

if __name__ == "__main__":
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
    db.init_app(app)
    with app.app_context():
        assemble_pfx()