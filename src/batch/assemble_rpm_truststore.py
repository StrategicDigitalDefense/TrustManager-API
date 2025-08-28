import os
import sys
sys.path.append('../db')
sys.path.append('../models')
import subprocess
import tempfile
from db.database import db_session
from models.certificates import Certificate

RPM_NAME = "trusted-certs"
RPM_VERSION = "1.0.0"
RPM_RELEASE = "1"
RPM_ARCH = "noarch"
RPM_OUTPUT = "trusted-certs-1.0.0-1.noarch.rpm"
CERTS_DIR = "/etc/pki/ca-trust/source/anchors"

def assemble_rpm():
    trusted_certs = Certificate.query.filter_by(trusted=True).all()
    if not trusted_certs:
        print("No trusted certificates found.")
        return

    with tempfile.TemporaryDirectory() as build_root:
        anchors_dir = os.path.join(build_root, CERTS_DIR.lstrip("/"))
        os.makedirs(anchors_dir, exist_ok=True)

        # Write each cert as a separate file and set permissions/ownership
        for idx, cert in enumerate(trusted_certs):
            filename = f"trusted_cert_{idx}.pem"
            cert_path = os.path.join(anchors_dir, filename)
            with open(cert_path, "w") as f:
                f.write(cert.pem.strip() + "\n")
            os.chmod(cert_path, 0o644)
            try:
                os.chown(cert_path, 0, 0)  # root:root
            except PermissionError:
                print(f"Warning: Could not change ownership of {cert_path}. Run as root for correct ownership.")

        # Create the spec file
        spec_path = os.path.join(build_root, "trusted-certs.spec")
        with open(spec_path, "w") as spec:
            spec.write(f"""
Name:           {RPM_NAME}
Version:        {RPM_VERSION}
Release:        {RPM_RELEASE}
Summary:        Trusted certificates from TrustManager API
License:        ASL 2.0
BuildArch:      {RPM_ARCH}
Requires(post): update-ca-trust
Requires(postun): update-ca-trust

%description
Trusted certificates from TrustManager API.

%files
%attr(0644,root,root) {CERTS_DIR}/*

%post
update-ca-trust enable
update-ca-trust extract

%postun
update-ca-trust extract

%prep
%build
%install
mkdir -p $RPM_BUILD_ROOT{CERTS_DIR}
cp -a {anchors_dir}/* $RPM_BUILD_ROOT{CERTS_DIR}/

%clean
rm -rf $RPM_BUILD_ROOT
""")

        # Build the RPM
        rpmbuild_cmd = [
            "rpmbuild",
            "--define", f"_topdir {build_root}",
            "--buildroot", build_root,
            "-bb", spec_path
        ]
        subprocess.run(rpmbuild_cmd, check=True)

        # Copy the RPM to the current directory
        rpm_file = os.path.join(build_root, "RPMS", RPM_ARCH, RPM_OUTPUT)
        if os.path.exists(rpm_file):
            os.rename(rpm_file, RPM_OUTPUT)
            print(f"RPM assembled at {RPM_OUTPUT}")
        else:
            print("RPM build failed.")

if __name__ == "__main__":
    assemble_rpm()