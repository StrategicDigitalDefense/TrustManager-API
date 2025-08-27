import os
import subprocess
import tempfile
from ..db.database import db_session
from ..models.certificates import Certificate

JKS_PATH = "trusted_certs.jks"
JKS_PASSWORD = "changeit"

def assemble_jks():
    # Remove existing JKS if present
    if os.path.exists(JKS_PATH):
        os.remove(JKS_PATH)

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
    assemble_jks()