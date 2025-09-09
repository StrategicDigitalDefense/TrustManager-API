from flask import Flask # type: ignore
from db.database import db
from models.certificates import Certificate  # <-- Import your model here!
from routes.certificates import certificates_bp
from waitress import serve

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
db.init_app(app)  # <-- This is required

with app.app_context():
    db.create_all()  # Optional: creates tables if not present

app.register_blueprint(certificates_bp)

if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5100, debug=True)
    serve(app, host="0.0.0.0", port=5100)