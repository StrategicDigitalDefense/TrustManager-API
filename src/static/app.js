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
            <td>${cert.serial}</td>
            <td>${cert.validFrom}</td>
            <td>${cert.validTo}</td>
            <td>${cert.trusted ? 'Yes' : 'No'}</td>
            <td>
                <button onclick="trustCert(${cert.id})" >Trust</button>
                <button onclick="distrustCert(${cert.id})" >Distrust</button>
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

function runBatchJob() {
    const job = document.getElementById('batchJobSelect').value;
    document.getElementById('batchJobMsg').textContent = "Running...";
    fetch('/BatchJob', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job })
    })
    .then(res => res.json())
    .then(data => {
        if (data.message) {
            document.getElementById('batchJobMsg').textContent = data.message;
        } else if (data.error) {
            document.getElementById('batchJobMsg').textContent = data.error;
        }
        if (data.stdout) {
            document.getElementById('batchJobMsg').textContent += "\n" + data.stdout;
        }
        if (data.stderr) {
            document.getElementById('batchJobMsg').textContent += "\n" + data.stderr;
        }
    })
    .catch(() => {
        document.getElementById('batchJobMsg').textContent = "Error running batch job.";
    });
}

function loadBatchJobs() {
    fetch('/BatchJob/list')
        .then(res => res.json())
        .then(jobs => {
            const select = document.getElementById('batchJobSelect');
            select.innerHTML = '';
            jobs.forEach(job => {
                const opt = document.createElement('option');
                opt.value = job;
                opt.textContent = job.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                select.appendChild(opt);
            });
        });
}

function loadGpoZips() {
    fetch('/Truststore/gpo/list')
        .then(res => res.json())
        .then(zips => {
            const ul = document.getElementById('gpoZipList');
            ul.innerHTML = '';
            zips.forEach(zip => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '/Truststore/gpo/' + encodeURIComponent(zip);
                a.textContent = zip;
                a.download = zip;
                li.appendChild(a);
                ul.appendChild(li);
            });
        });
}

document.addEventListener('DOMContentLoaded', function() {
    fetchCertificates();
    loadBatchJobs();
    loadGpoZips();
});