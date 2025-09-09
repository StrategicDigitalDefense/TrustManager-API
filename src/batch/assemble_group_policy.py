import os
import sys
from flask import Flask # type: ignore
import uuid
import shutil

# Ensure src/ is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cryptography import x509 # type: ignore
from cryptography.hazmat.primitives import serialization # type: ignore
from db.database import db
from models.certificates import Certificate

def export_gpo_trusted_roots(output_dir="static/GPO_Backup"):
    # Generate a new GUID for the GPO backup
    gpo_guid = str(uuid.uuid4()).upper()
    gpo_path = os.path.join(output_dir, gpo_guid, "DomainSysvol", "GPO", "Machine", "Microsoft", "Windows", "SecEdit")
    os.makedirs(gpo_path, exist_ok=True)

    # Query all trusted certificates
    trusted_certs = Certificate.query.filter_by(trusted=True).all()
    cert_filenames = []

    for idx, cert in enumerate(trusted_certs):
        cert_obj = x509.load_pem_x509_certificate(cert.pem.encode())
        der_bytes = cert_obj.public_bytes(serialization.Encoding.DER)
        cert_filename = f"trusted_root_{idx+1}.cer"
        cert_path = os.path.join(gpo_path, cert_filename)
        with open(cert_path, "wb") as f:
            f.write(der_bytes)
        cert_filenames.append(cert_filename)

    # Write GptTmpl.inf referencing the certs
    inf_path = os.path.join(gpo_path, "GptTmpl.inf")
    with open(inf_path, "w") as inf:
        inf.write("[Version]\nsignature=\"$CHICAGO$\"\nRevision=1\n\n")
        inf.write("[Registry Values]\n\n")
        inf.write("[Unicode]\nUnicode=yes\n\n")
        inf.write("[System Access]\n\n")
        inf.write("[Event Audit]\n\n")
        inf.write("[Kerberos Policy]\n\n")
        inf.write("[Privilege Rights]\n\n")
        inf.write("[Public Key Policies]\n")
        for cert_filename in cert_filenames:
            inf.write(f'CertificateAuthority={cert_filename}\n')

    print(f"GPO backup created at: {os.path.abspath(os.path.join(output_dir, gpo_guid))}")

    # Zip the GPO backup folder
    zip_path = os.path.join(output_dir, f"{gpo_guid}.zip")
    shutil.make_archive(os.path.splitext(zip_path)[0], 'zip', os.path.join(output_dir, gpo_guid))
    print(f"GPO backup zip created at: {zip_path}")

if __name__ == "__main__":
    app = Flask(__name__) # type: ignore
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
    db.init_app(app)
    with app.app_context():
        export_gpo_trusted_roots()