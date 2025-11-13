from db.database import db

class Contact(db.Model):
    __tablename__ = 'CONTACTS'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    contact = db.Column(db.String, nullable=False)