import os
import sys
sys.path.append('../db')
sys.path.append('../models')
from db.database import db_session
from models.certificates import Certificate

OUTPUT_PATH = "trusted_certs.pem"

def assemble_trusted_pem():
    trusted_certs = Certificate.query.filter_by(trusted=True).all()
    if not trusted_certs:
        print("No trusted certificates found.")
        return

    with open(OUTPUT_PATH, "w") as out_file:
        for cert in trusted_certs:
            out_file.write(f"## {cert.subject}\n")
            out_file.write(f"## {cert.valid_to}\n")
            out_file.write(cert.pem.strip() + "\n\n")
    print(f"Concatenated PEM written to {OUTPUT_PATH}")

if __name__ == "__main__":
    assemble_trusted_pem()