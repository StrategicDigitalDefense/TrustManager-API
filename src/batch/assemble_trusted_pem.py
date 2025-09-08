import sys
import os

# Ensure src/ is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from flask import Flask
from db.database import db
from models.certificates import Certificate

OUTPUT_PATH = "static/trusted_certs.pem"

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
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
    db.init_app(app)
    with app.app_context():
        assemble_trusted_pem()