from flask import Flask, config # type: ignore
from db.database import db
from models.certificates import Certificate  # <-- Import your model here!
from routes.certificates import certificates_bp
from waitress import serve # type: ignore
from authlib.integrations.flask_client import OAuth # type: ignore
import os


app = Flask(__name__)
with app.app_context():
    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['TRUSTMANAGER_DATABASE_URL']
    except KeyError:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
    try:
        if os.environ['TRUSTMANAGER_REQUIRE_AUTH'].lower() in [
            'true', '1', 't', 'yes', 'y'
        ]:
            app.config['AUTH'] = True
        else:
            app.config['AUTH'] = False
    except KeyError:
        app.config['AUTH'] = False

    if app.config['AUTH']:
        try:
            app.config['OIDC_CLIENT_ID'] = os.environ['TRUSTMANAGER_OIDC_CLIENT_ID']
            app.config['OIDC_CLIENT_SECRET'] = os.environ['TRUSTMANAGER_OIDC_CLIENT_SECRET']
            app.config['OIDC_METADATA_URL'] = os.environ['TRUSTMANAGER_OIDC_METADATA_URL']  
        except KeyError:
            app.config['AUTH'] = False  # Disable auth if OIDC config is missing
    db.init_app(app)  # <-- This is required

    with app.app_context():
        db.create_all()  # Optional: creates tables if not present

    app.register_blueprint(certificates_bp)



if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5100, debug=True)
    serve(app, host="0.0.0.0", port=5100)