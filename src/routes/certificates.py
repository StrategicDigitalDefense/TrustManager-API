from flask import Blueprint, request, jsonify, Response, url_for, send_file, send_from_directory, abort, redirect # type: ignore
#from flask import abort
from datetime import datetime
from cryptography import x509 # type: ignore
from cryptography.hazmat.primitives import hashes, serialization # type: ignore
from cryptography.hazmat.backends import default_backend # type: ignore
from xml.sax.saxutils import escape
import sys
import os
import glob
import logging
sys.path.append('../')
sys.path.append('../models')
sys.path.append('../db')
from models.certificates import Certificate
from db.database import *
import syslog
import subprocess
from functools import wraps
from app import oauth, app

syslog.openlog("TrustManager-API",0,syslog.LOG_LOCAL7)


certificates_bp = Blueprint('certificates', __name__)

def parse_certificate(pem_data):
    syslog.syslog(syslog.LOG_DEBUG,"Calling parse_certificate() with PEM payload\n%s" % (pem_data))
    cert = x509.load_pem_x509_certificate(pem_data.encode(), default_backend())
    subject = cert.subject.rfc4514_string()
    issuer = cert.issuer.rfc4514_string()
    valid_from = cert.not_valid_before
    valid_to = cert.not_valid_after
    serial = str(cert.serial_number)
    fingerprint = cert.fingerprint(hashes.SHA256()).hex()
    syslog.syslog(
        syslog.LOG_DEBUG,
        {
            'subject': subject,
            'issuer': issuer,
            'valid_from': valid_from,
            'valid_to': valid_to,
            'serial': serial,
            'fingerprint': fingerprint
        }
    )
    return {
        'subject': subject,
        'issuer': issuer,
        'valid_from': valid_from,
        'valid_to': valid_to,
        'serial': serial,
        'fingerprint': fingerprint
    }


def require_oidc_role(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verify the Authorization header
            if app.config['AUTH'] == True:
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return jsonify({'error': 'Unauthorized'}), 401

                token = auth_header.split(' ')[1]

                try:
                    # Decode and validate the token
                    claims = oauth.oidc.parse_id_token(token)
                except Exception as e:
                    return jsonify({'error': f'Invalid token: {str(e)}'}), 401

                # Check for the required role in the Roles claim
                roles = claims.get('roles', [])
                if required_role not in roles:
                    return jsonify({'error': 'Forbidden: insufficient role'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


@certificates_bp.route('/Certificate', methods=['PUT'])
@require_oidc_role('TrustAdmin')
def add_certificate():
    pem_data = request.json.get('pem')
    if not pem_data:
        return jsonify({'error': 'PEM data is required'}), 400
    try:
        fields = parse_certificate(pem_data)
    except Exception as e:
        logging.error(f"Certificate parsing failed: {str(e)}")
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

    try:
        db.session.add(new_certificate)
        db.session.commit()
    except Exception as e:
        logging.error(f"Database operation failed: {str(e)}")
        return jsonify({'error': 'Failed to save certificate to the database.'}), 500

    return jsonify({'message': 'Certificate added successfully'}), 201

@certificates_bp.route('/Certificates', methods=['GET'])
def get_certificates():
    syslog.syslog(syslog.LOG_DEBUG,"Calling get_certificates()")
    certificates = Certificate.query.all()
    syslog.syslog(syslog.LOG_DEBUG,"Returning %i responses" % (len(certificates)))
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
@require_oidc_role('TrustAdmin')
def trust_certificate():
    cert_id = request.json.get('id')
    syslog.syslog(syslog.LOG_DEBUG,"Calling trust_certificate() with certificate ID %i" % (cert_id))
    if not cert_id:
        syslog.syslog(syslog.LOG_INFO,'Certificate ID is required')
        return jsonify({'error': 'Certificate ID is required'}), 400

    certificate = Certificate.query.get(cert_id)
    if not certificate:
        syslog.syslog(syslog.LOG_INFO,'Certificate not found: id=%i' % cert_id)
        return jsonify({'error': 'Certificate not found'}), 404

    # Only allow trusting if subject and issuer match (self-signed)
    if certificate.subject != certificate.issuer:
        syslog.syslog(syslog.LOG_INFO,'Only self-signed certificates (subject == issuer) can be trusted.')
        return jsonify({'error': 'Only self-signed certificates (subject == issuer) can be trusted.'}), 403

    certificate.trusted = True
    certificate.last_changed = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Certificate trusted successfully'}), 200

@certificates_bp.route('/Distrust', methods=['POST'])
@require_oidc_role('TrustAdmin')
def distrust_certificate():
    cert_id = request.json.get('id')
    if not cert_id:
        syslog.syslog(syslog.LOG_INFO,'Certificate ID is required')
        return jsonify({'error': 'Certificate ID is required'}), 400

    certificate = Certificate.query.get(cert_id)
    if not certificate:
        syslog.syslog(syslog.LOG_INFO,'Certificate not found: id=%i' % (cert_id))
        return jsonify({'error': 'Certificate not found'}), 404

    certificate.trusted = False
    certificate.last_changed = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Certificate distrusted successfully'}), 200

@certificates_bp.route('/Certificate/serial/<serial>', methods=['GET'])
def get_certificate_by_serial(serial):
    syslog.syslog(syslog.LOG_DEBUG,"Calling get_certificate_by_serial() wth serial number %s" % (serial))
    certificate = Certificate.query.filter_by(serial=serial).first()
    if not certificate:
        syslog.syslog(syslog.LOG_INFO,'Certificate not found: serial=%s' % (serial))
        return jsonify({'error': 'Certificate not found'}), 404
    return certificate.pem, 200

@certificates_bp.route('/Certificate/subject/<subject>', methods=['GET'])
def get_certificate_by_subject(subject):
    syslog.syslog(syslog.LOG_DEBUG,"Calling get_certificate_by_subject() with subject filter %s" % (subject))
    certificates = Certificate.query.filter(Certificate.subject.like(f"%{subject}%")).all()
    if not certificates:
        syslog.syslog(syslog.LOG_INFO,'No certificates found matching subject filter: %s' % (subject))
        return jsonify({'error': 'No certificates found'}), 404
    return [cert.pem for cert in certificates], 200

@certificates_bp.route('/Certificate/fingerprint/<fingerprint>', methods=['GET'])
def get_certificate_by_fingerprint(fingerprint):
    syslog.syslog(syslog.LOG_DEBUG,"Calling get_certificate_by_fingerprint() with fingerprint %s" % (fingerprint))
    certificate = Certificate.query.filter_by(fingerprint=fingerprint).first()
    if not certificate:
        syslog.syslog(syslog.LOG_INFO,'Certificate not found: fingerprint=%s' % (fingerprint))
        return jsonify({'error': 'Certificate not found'}), 404
    return certificate.pem, 200

def generate_atom_feed(certificates):
    syslog.syslog(syslog.LOG_DEBUG,"Calling generate_atom_feed() with %i certificates" % (len(certificates)))
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
    syslog.syslog(syslog.LOG_DEBUG,"Calling trusted_certificates_feed()")
    certificates = Certificate.query.filter_by(trusted=True).all()
    atom_xml = generate_atom_feed(certificates)
    return Response(atom_xml, mimetype='application/atom+xml')

TRUSTSTORE_FILES = {
    "jks": "/static/trusted_certs.jks",
    "pfx": "/static/trusted_certs.pfx",
    "pem": "/static/trusted_certs.pem",
    "rpm": "/static/trusted-certs-1.0.0-1.noarch.rpm"
}

@certificates_bp.route('/Truststore/<format>', methods=['GET'])
def get_truststore_file(format):
    """
    Retrieve the truststore file in the specified format.
    Supported formats: jks, pfx, pem, rpm
    """
    filename = TRUSTSTORE_FILES.get(format.lower())
    syslog.syslog(syslog.LOG_DEBUG,"Calling get_truststore_file() with format %s" % (format))
    syslog.syslog(syslog.LOG_DEBUG,"Resolved filename: %s" % (filename))
    #if not filename or not os.path.exists(filename):
    #    return jsonify({'error': f'Truststore file for format "{format}" not found.'}), 404
    #return send_file(filename, as_attachment=True)
    #return(redirect(f'/static/{os.path.basename(filename)}'))
    return send_from_directory('static', os.path.basename(filename), as_attachment=True)


@certificates_bp.route('/admin')
def admin_gui():
    return send_from_directory('static', 'index.html')

#@certificates_bp.route('/swagger')
#def swagger_ui():
#    return send_from_directory('static', 'swagger.html')
#

BATCH_JOBS = {
    "assemble_jks": "batch/assemble_jks.py",
    "assemble_pfx": "batch/assemble_pfx.py",
    "assemble_trusted_pem": "batch/assemble_trusted_pem.py",
    "assemble_rpm": "batch/assemble_rpm.py",
    "assemble_group_policy": "batch/assemble_group_policy.py"
}

@certificates_bp.route('/BatchJob', methods=['POST'])
@require_oidc_role('TrustAdmin')
def run_batch_job():
    """
    Initiate a batch job by name.
    Request JSON: { "job": "<job_name>" }
    """
    job_name = request.json.get("job")
    syslog.syslog(syslog.LOG_DEBUG,"Calling run_batch_job() with job name: %s" % (job_name))
    if not job_name or job_name not in BATCH_JOBS:
        syslog.syslog(syslog.LOG_INFO,'Invalid or missing job name in request.')
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

@certificates_bp.route('/BatchJob/list', methods=['GET'])
def list_batch_jobs():
    # BATCH_JOBS should be defined at module level
    syslog.syslog(syslog.LOG_DEBUG,"Calling list_batch_jobs()")
    return jsonify(list(BATCH_JOBS.keys()))

@certificates_bp.route('/Truststore/gpo', methods=['GET'])
def download_latest_gpo_zip():
    syslog.syslog(syslog.LOG_DEBUG,"Calling download_latest_gpo_zip()")
    gpo_dir = os.path.join('static', 'GPO_Backup')
    zip_files = sorted(
        glob.glob(os.path.join(gpo_dir, '*.zip')),
        key=os.path.getmtime,
        reverse=True
    )
    if not zip_files:
        syslog.syslog(syslog.LOG_INFO,'No GPO backup zip files found.')
        return jsonify({'error': 'No GPO backup zip found.'}), 404
    return send_file(zip_files[0], as_attachment=True)

@certificates_bp.route('/Truststore/gpo/list', methods=['GET'])
def list_gpo_zips():
    syslog.syslog(syslog.LOG_DEBUG,"Calling list_gpo_zips()")
    gpo_dir = os.path.join('static', 'GPO_Backup')
    zip_files = sorted(
        glob.glob(os.path.join(gpo_dir, '*.zip')),
        key=os.path.getmtime,
        reverse=True
    )
    # Return just the filenames (not full paths)
    syslog.syslog(syslog.LOG_DEBUG,"Found %i GPO backup zip files" % (len(zip_files)))
    syslog.syslog(syslog.LOG_DEBUG,"GPO backup zip files: %s" % (zip_files))
    return jsonify([os.path.basename(z) for z in zip_files])

@certificates_bp.route('/Truststore/gpo/<zipname>', methods=['GET'])
def download_specific_gpo_zip(zipname):
    syslog.syslog(syslog.LOG_DEBUG,"Calling download_specific_gpo_zip() with zip name: %s" % (zipname))
    gpo_dir = os.path.join('static', 'GPO_Backup')
    zip_path = os.path.join(gpo_dir, zipname)
    if not os.path.exists(zip_path):
        syslog.syslog(syslog.LOG_INFO,'Requested GPO backup zip not found: %s' % (zipname))
        return jsonify({'error': 'GPO backup zip not found.'}), 404
    return send_file(zip_path, as_attachment=True)
