from flask import Blueprint, request, jsonify, Response, url_for, send_file, send_from_directory, abort # type: ignore
#from flask import abort
from datetime import datetime
from cryptography import x509 # type: ignore
from cryptography.hazmat.primitives import hashes, serialization # type: ignore
from cryptography.hazmat.backends import default_backend # type: ignore
from xml.sax.saxutils import escape
import sys
import os
sys.path.append('../models')
sys.path.append('../db')
from models.certificates import Certificate
from db.database import *


certificates_bp = Blueprint('certificates', __name__)

def parse_certificate(pem_data):
    cert = x509.load_pem_x509_certificate(pem_data.encode(), default_backend())
    subject = cert.subject.rfc4514_string()
    issuer = cert.issuer.rfc4514_string()
    valid_from = cert.not_valid_before
    valid_to = cert.not_valid_after
    serial = str(cert.serial_number)
    fingerprint = cert.fingerprint(hashes.SHA256()).hex()
    return {
        'subject': subject,
        'issuer': issuer,
        'valid_from': valid_from,
        'valid_to': valid_to,
        'serial': serial,
        'fingerprint': fingerprint
    }

@certificates_bp.route('/Certificate', methods=['PUT'])
def add_certificate():
    #pem_data = request.json.get('pem')
    pem_data = request.data.decode('utf-8') # Read raw data from request body
    if not pem_data:
        return jsonify({'error': 'PEM data is required'}), 400

    try:
        fields = parse_certificate(pem_data)
    except Exception as e:
        return jsonify({'error': f'Failed to parse certificate: {str(e)}'}), 400

    new_certificate = Certificate(
        subject=fields['subject'],
        issuer=fields['issuer'],
        valid_from=fields['valid_from'],
        valid_to=fields['valid_to'],
        pem=pem_data,
        serial=fields['serial'],
        fingerprint=fields['fingerprint'],
        uploaded=datetime.utcnow(),
        last_changed=datetime.utcnow(),
        trusted=False
    )

    db.session.add(new_certificate)
    db.session.commit()

    return jsonify({'message': 'Certificate added successfully'}), 201

@certificates_bp.route('/Certificates', methods=['GET'])
def get_certificates():
    certificates = Certificate.query.all()
    return [{
        'id': cert.id,
        'subject': cert.subject,
        'validFrom': cert.valid_from.strftime('%Y-%m-%d'),
        'validTo': cert.valid_to.strftime('%Y-%m-%d'),
        'serial': cert.serial,
        'fingerprint': cert.fingerprint,
        'trusted': cert.trusted,
        'certificate': cert.pem
    } for cert in certificates], 200

@certificates_bp.route('/Trust', methods=['POST'])
def trust_certificate():
    cert_id = request.json.get('id')
    if not cert_id:
        return jsonify({'error': 'Certificate ID is required'}), 400

    certificate = Certificate.query.get(cert_id)
    if not certificate:
        return jsonify({'error': 'Certificate not found'}), 404

    # Only allow trusting if subject and issuer match (self-signed)
    if certificate.subject != certificate.issuer:
        return jsonify({'error': 'Only self-signed certificates (subject == issuer) can be trusted.'}), 403

    certificate.trusted = True
    certificate.last_changed = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Certificate trusted successfully'}), 200

@certificates_bp.route('/Distrust', methods=['POST'])
def distrust_certificate():
    cert_id = request.json.get('id')
    if not cert_id:
        return jsonify({'error': 'Certificate ID is required'}), 400

    certificate = Certificate.query.get(cert_id)
    if not certificate:
        return jsonify({'error': 'Certificate not found'}), 404

    certificate.trusted = False
    certificate.last_changed = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Certificate distrusted successfully'}), 200

@certificates_bp.route('/Certificate/serial/<serial>', methods=['GET'])
def get_certificate_by_serial(serial):
    certificate = Certificate.query.filter_by(serial=serial).first()
    if not certificate:
        return jsonify({'error': 'Certificate not found'}), 404
    return certificate.pem, 200

@certificates_bp.route('/Certificate/subject/<subject>', methods=['GET'])
def get_certificate_by_subject(subject):
    certificates = Certificate.query.filter(Certificate.subject.like(f"%{subject}%")).all()
    if not certificates:
        return jsonify({'error': 'No certificates found'}), 404
    return [cert.pem for cert in certificates], 200

@certificates_bp.route('/Certificate/fingerprint/<fingerprint>', methods=['GET'])
def get_certificate_by_fingerprint(fingerprint):
    certificate = Certificate.query.filter_by(fingerprint=fingerprint).first()
    if not certificate:
        return jsonify({'error': 'Certificate not found'}), 404
    return certificate.pem, 200

def generate_atom_feed(certificates):
    updated = max([cert.last_changed for cert in certificates]) if certificates else datetime.utcnow()
    feed = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f'<title>Trusted Certificates Feed</title>',
        f'<updated>{updated.isoformat()}Z</updated>',
        f'<id>{escape(url_for("certificates.trusted_certificates_feed", _external=True))}</id>'
    ]
    for cert in certificates:
        feed.append('<entry>')
        feed.append(f'<title>{escape(cert.subject)}</title>')
        feed.append(f'<id>{escape(url_for("certificates.get_certificate_by_serial", serial=cert.serial, _external=True))}</id>')
        feed.append(f'<updated>{cert.last_changed.isoformat()}Z</updated>')
        feed.append(f'<summary>Issuer: {escape(cert.issuer)}, Expires: {cert.valid_to}</summary>')
        feed.append(f'<content type="text">{escape(cert.pem)}</content>')
        feed.append('</entry>')
    feed.append('</feed>')
    return '\n'.join(feed)

@certificates_bp.route('/Certificates/atom', methods=['GET'])
def trusted_certificates_feed():
    certificates = Certificate.query.filter_by(trusted=True).all()
    atom_xml = generate_atom_feed(certificates)
    return Response(atom_xml, mimetype='application/atom+xml')

TRUSTSTORE_FILES = {
    "jks": "trusted_certs.jks",
    "pfx": "trusted_certs.pfx",
    "pem": "trusted_certs.pem",
    "rpm": "trusted-certs-1.0.0-1.noarch.rpm"
}

@certificates_bp.route('/Truststore/<format>', methods=['GET'])
def get_truststore_file(format):
    """
    Retrieve the truststore file in the specified format.
    Supported formats: jks, pfx, pem, rpm
    """
    filename = TRUSTSTORE_FILES.get(format.lower())
    if not filename or not os.path.exists(filename):
        return jsonify({'error': f'Truststore file for format "{format}" not found.'}), 404
    return send_file(filename, as_attachment=True)

@certificates_bp.route('/admin')
def admin_gui():
    return send_from_directory('static', 'index.html')

#@certificates_bp.route('/swagger')
#def swagger_ui():
#    return send_from_directory('static', 'swagger.html')
#

BATCH_JOBS = {
    "assemble_jks": "src/batch/assemble_jks.py",
    "assemble_pfx": "src/batch/assemble_pfx.py",
    "assemble_trusted_pem": "src/batch/assemble_trusted_pem.py",
    "assemble_rpm": "src/batch/assemble_rpm.py",
    "assemble_group_policy": "src/batch/assemble_group_policy.py"
}

import subprocess

@certificates_bp.route('/BatchJob', methods=['POST'])
def run_batch_job():
    """
    Initiate a batch job by name.
    Request JSON: { "job": "<job_name>" }
    """
    job_name = request.json.get("job")
    if not job_name or job_name not in BATCH_JOBS:
        return jsonify({"error": "Invalid or missing job name.", "available_jobs": list(BATCH_JOBS.keys())}), 400

    script_path = BATCH_JOBS[job_name]
    try:
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({
            "message": f"Batch job '{job_name}' executed successfully.",
            "stdout": result.stdout,
            "stderr": result.stderr
        }), 200
    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": f"Batch job '{job_name}' failed.",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500