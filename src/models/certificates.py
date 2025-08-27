from db.database import db

class Certificate(db.Model):
    __tablename__ = 'CERTIFICATES'
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String, nullable=False)
    issuer = db.Column(db.String, nullable=False)
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_to = db.Column(db.DateTime, nullable=False)
    pem = db.Column(db.Text, nullable=False)
    serial = db.Column(db.String, nullable=False)
    fingerprint = db.Column(db.String, nullable=False)
    uploaded = db.Column(db.DateTime, nullable=False)
    last_changed = db.Column(db.DateTime, nullable=False)
    trusted = db.Column(db.Boolean, default=False)