FROM registry.access.redhat.com/ubi9/ubi
WORKDIR /opt/TrustManager-API/
RUN yum -y install python39 python3-pip
COPY requirements.txt .
COPY license.txt .
RUN python3 -m pip install -v -r requirements.txt
RUN yum -y install java-17-openjdk-devel
RUN yum -y install openssl openssl-devel
RUN yum -y install bash
COPY src/ .
EXPOSE 5100
CMD ["python3.9", "app.py"]
#
# To build:
# docker build -t flask-certificates-api .
#
# To run:
# docker run -d -p 5100:5100 --name flask-certificates-api
#
# Then browse to http://localhost:5100/admin in browser
#
#