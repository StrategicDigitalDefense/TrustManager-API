import os
import sys
sys.path.append('../db')
sys.path.append('../models')
import subprocess
import tempfile
from db.database import db_session
from models.certificates import Certificate

PFX_PATH = "trusted_certs.pfx"
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
    assemble_pfx()