# Start with RHEL UBI 9 base image, because we want it for buiding RPM packages later
# and it has good support for Python 3.9 and Java 17
# See https://developers.redhat.com/articles/ubi-and-python
FROM registry.access.redhat.com/ubi9/ubi
WORKDIR /opt/TrustManager-API/
# This is mostly Python, so of course we need Python
RUN yum -y install python39 python3-pip
COPY requirements.txt .
COPY license.txt .
RUN python3 -m pip install -v -r requirements.txt
# Need JDK so we get keytool for creating keystores and truststores 
RUN yum -y install java-17-openjdk-devel
# Need openssl for creating PKCS#12 (PFX) bundles
RUN yum -y install openssl openssl-devel
# Bash, just in case we have to get an interactive TTY in there
RUN yum -y install bash
COPY src/ .
# We run on port 5100, because reasons
EXPOSE 5100
CMD ["python3.9", "app.py"]
#
# To build:
# docker build -t trustmanager-api . 
#
# To run:
# docker run -it -p 5100:5100 trustmanager-api 
#
# Then browse to http://localhost:5100/admin in browser
#
#