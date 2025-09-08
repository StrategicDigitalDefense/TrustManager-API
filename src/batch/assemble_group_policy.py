import os
import uuid
from cryptography import x509
from cryptography.hazmat.primitives import serialization
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

if __name__ == "__main__":
    export_gpo_trusted_roots()