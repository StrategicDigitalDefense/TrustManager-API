from db.database import db
from datetime import datetime

class Truststore(db.Model):
    __tablename__ = 'TRUSTSTORES'

    id = db.Column(db.Integer, primary_key=True)
    truststore_type = db.Column(db.String, nullable=False)  # JKS, PKCS12, CAPI, PEM File(s)
    host = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)
    last_reviewed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=False, default="")  # Append-only text field
    contact_id = db.Column(db.Integer, db.ForeignKey('CONTACTS.id'), nullable=True)  # New field
    contact = db.relationship('Contact', backref=db.backref('truststores', lazy=True))

class TruststoreCertificate(db.Model):
    __tablename__ = 'TRUSTSTORE_CERTIFICATES'

    id = db.Column(db.Integer, primary_key=True)
    truststore_id = db.Column(db.Integer, db.ForeignKey('TRUSTSTORES.id'), nullable=False)
    certificate_id = db.Column(db.Integer, db.ForeignKey('CERTIFICATES.id'), nullable=False)

    truststore = db.relationship('Truststore', backref=db.backref('certificates', lazy=True))
    certificate = db.relationship('Certificate', backref=db.backref('truststores', lazy=True))