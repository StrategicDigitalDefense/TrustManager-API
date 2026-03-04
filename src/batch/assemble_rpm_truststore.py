import sys
import os
import tempfile
import subprocess
import shutil

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from flask import Flask # type: ignore
from db.database import db
from models.certificates import Certificate

RPM_NAME = "trusted-certs"
RPM_VERSION = "1.0.0"
RPM_RELEASE = "1"
RPM_ARCH = "noarch"
RPM_FILENAME = f"{RPM_NAME}-{RPM_VERSION}-{RPM_RELEASE}.{RPM_ARCH}.rpm"
RPM_OUTPUT = os.path.join("static", RPM_FILENAME)
CERTS_DIR = "/etc/pki/ca-trust/source/anchors"

def assemble_rpm():
    trusted_certs = Certificate.query.filter_by(trusted=True).all()
    if not trusted_certs:
        print("No trusted certificates found.")
        return

    print(f"Number of trusted certificates: {len(trusted_certs)}")

    with tempfile.TemporaryDirectory() as build_root:
        buildroot_dir = os.path.join(build_root, "BUILDROOT")
        build_dir = os.path.join(build_root, "BUILD")
        rpms_dir = os.path.join(build_root, "RPMS")
        sources_dir = os.path.join(build_root, "SOURCES")
        specs_dir = os.path.join(build_root, "SPECS")
        srpms_dir = os.path.join(build_root, "SRPMS")
        for directory in (build_root, buildroot_dir, build_dir, rpms_dir, sources_dir, specs_dir, srpms_dir):
            os.makedirs(directory, exist_ok=True)

        staged_certs_dir = os.path.join(sources_dir, "certs")
        os.makedirs(staged_certs_dir, exist_ok=True)

        # Write each cert as a separate file for the payload
        for idx, cert in enumerate(trusted_certs):
            filename = f"trusted_cert_{idx}.pem"
            cert_path = os.path.join(staged_certs_dir, filename)
            with open(cert_path, "w") as f:
                f.write(cert.pem.strip() + "\n")
            os.chmod(cert_path, 0o644)
            print(f"Certificate staged at: {cert_path}")

        files_section = "\n".join(
            f"%attr(0644,root,root) {CERTS_DIR}/{filename}"
            for filename in sorted(os.listdir(staged_certs_dir))
        )
        print(f"%files section:\n{files_section}")

        spec_path = os.path.join(specs_dir, f"{RPM_NAME}.spec")
        with open(spec_path, "w") as spec:
            spec.write(f"""
Name:               {RPM_NAME}
Version:            {RPM_VERSION}
Release:            {RPM_RELEASE}
Summary:            Trusted certificates from TrustManager API
BuildArch:          {RPM_ARCH}
License:            BSD Four-Clause License
Requires:           ca-certificates
Requires(post):     update-ca-trust
Requires(postun):   update-ca-trust

%description
Trusted certificates from TrustManager API.

%prep
%build
%install
mkdir -p %{{buildroot}}{CERTS_DIR}
cp -p %{{_sourcedir}}/certs/*.pem %{{buildroot}}{CERTS_DIR}/

%files
{files_section}

%post
/usr/bin/update-ca-trust

%postun
/usr/bin/update-ca-trust

%clean
""")

        rpmbuild_cmd = [
            "rpmbuild",
            "--define", f"_topdir {build_root}",
            "--buildroot", buildroot_dir,
            "-bb", spec_path
        ]
        print(f"Running rpmbuild command: {' '.join(rpmbuild_cmd)}")
        subprocess.run(rpmbuild_cmd, check=True)

        rpm_file = os.path.join(rpms_dir, RPM_ARCH, RPM_FILENAME)
        if os.path.exists(rpm_file):
            os.makedirs(os.path.dirname(RPM_OUTPUT), exist_ok=True)
            shutil.copy2(rpm_file, RPM_OUTPUT)
            print(f"RPM assembled at {RPM_OUTPUT}")
        else:
            print("RPM build failed.")

if __name__ == "__main__":
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
    db.init_app(app)
    with app.app_context():
        assemble_rpm()