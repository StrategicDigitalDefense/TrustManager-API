function addCertificate() {
    const pem = document.getElementById('pemInput').value;
    fetch('/Certificate', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pem })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('addCertMsg').textContent = data.message || data.error || '';
        fetchCertificates();
    })
    .catch(err => {
        document.getElementById('addCertMsg').textContent = 'Error adding certificate.';
    });
}

function fetchCertificates() {
    fetch('/Certificates')
    .then(res => res.json())
    .then(data => {
        renderCertTable(data);
        window.allCertificates = data;
    })
    .catch(() => {
        document.getElementById('certMsg').textContent = 'Error fetching certificates.';
    });
}

function renderCertTable(certificates) {
    const tbody = document.querySelector('#certTable tbody');
    tbody.innerHTML = '';
    certificates.forEach(cert => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${cert.id}</td>
            <td>${cert.subject}</td>
            <td>${cert.issuer}</td>
            <td>${cert.serial}</td>
            <td>${cert.valid_from}</td>
            <td>${cert.valid_to}</td>
            <td>${cert.trusted ? 'Yes' : 'No'}</td>
            <td>
                <button onclick="trustCert(${cert.id})" ${cert.trusted || cert.subject !== cert.issuer ? 'disabled' : ''}>Trust</button>
                <button onclick="distrustCert(${cert.id})" ${!cert.trusted ? 'disabled' : ''}>Distrust</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function trustCert(id) {
    fetch('/Trust', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('certMsg').textContent = data.message || data.error || '';
        fetchCertificates();
    });
}

function distrustCert(id) {
    fetch('/Distrust', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('certMsg').textContent = data.message || data.error || '';
        fetchCertificates();
    });
}

function searchCertificates() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const filtered = (window.allCertificates || []).filter(cert =>
        cert.subject.toLowerCase().includes(query) ||
        cert.serial.toLowerCase().includes(query) ||
        cert.fingerprint && cert.fingerprint.toLowerCase().includes(query)
    );
    renderCertTable(filtered);
}

// Initial load
document.addEventListener('DOMContentLoaded', fetchCertificates);