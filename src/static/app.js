function addCertificate() {
    const pem = document.getElementById('pemInput').value;
    console.log("PEM being sent:", pem);
    fetch('/Certificate', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pem })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
    })
    .then(data => {
        document.getElementById('addCertMsg').textContent = data.message || data.error || '';
        fetchCertificates();
    })
    .catch(err => {
        console.error("Error adding certificate:", err);
        document.getElementById('addCertMsg').textContent = `Error adding certificate: ${err.message}`;
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

function addTruststore() {
    const truststoreType = document.getElementById('truststoreType').value;
    const host = document.getElementById('truststoreHost').value;
    const location = document.getElementById('truststoreLocation').value;
    const certificateIds = document.getElementById('truststoreCertificates').value.split(',').map(id => parseInt(id.trim()));
    const notes = document.getElementById('truststoreNotes').value;
    const contactId = document.getElementById('truststoreContact').value; // Get the selected contact ID

    fetch('/Governance/Truststore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            truststore_type: truststoreType,
            host,
            location,
            certificate_ids: certificateIds,
            notes,
            contact_id: parseInt(contactId) // Ensure it's sent as an integer
        })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('addTruststoreMsg').textContent = data.message || data.error;
        fetchTruststores();
    })
    .catch(err => {
        document.getElementById('addTruststoreMsg').textContent = 'Error adding truststore.';
    });
}

function fetchTruststores() {
    fetch('/Governance/Truststore')
    .then(res => res.json())
    .then(data => {
        const tbody = document.getElementById('truststoreTable').querySelector('tbody');
        tbody.innerHTML = '';
        data.forEach(truststore => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${truststore.id}</td>
                <td>${truststore.truststore_type}</td>
                <td>${truststore.host}</td>
                <td>${truststore.location}</td>
                <td>${truststore.last_reviewed}</td>
                <td>${truststore.notes}</td>
                <td>${truststore.contact ? `${truststore.contact.name} (${truststore.contact.contact})` : 'No Contact'}</td>
                <td>
                    <button onclick="selectTruststore(${truststore.id})">Select</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    })
    .catch(err => {
        document.getElementById('truststoreMsg').textContent = 'Error fetching truststores.';
    });
}

function addTruststoreNotes() {
    const truststoreId = document.getElementById('truststoreId').value;
    const notes = document.getElementById('truststoreNewNotes').value;

    fetch(`/Governance/Truststore/${truststoreId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('addTruststoreNotesMsg').textContent = data.message || data.error;
        fetchTruststores();
    })
    .catch(err => {
        document.getElementById('addTruststoreNotesMsg').textContent = 'Error adding notes.';
    });
}

function selectTruststore(id) {
    document.getElementById('truststoreId').value = id;
}

function addContact() {
    const name = document.getElementById('contactName').value;
    const contact = document.getElementById('contactInfo').value;

    fetch('/Contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, contact })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('addContactMsg').textContent = data.message || data.error;
        loadContacts();
    })
    .catch(err => {
        document.getElementById('addContactMsg').textContent = 'Error adding contact.';
    });
}

function loadContacts() {
    fetch('/Contacts')
        .then(res => res.json())
        .then(data => {
            // Populate the dropdown
            const select = document.getElementById('truststoreContact');
            select.innerHTML = ''; // Clear existing options
            data.forEach(contact => {
                const opt = document.createElement('option');
                opt.value = contact.id;
                opt.textContent = `${contact.name} (${contact.contact})`;
                select.appendChild(opt);
            });

            // Populate the table
            const tbody = document.getElementById('contactsTable').querySelector('tbody');
            tbody.innerHTML = ''; // Clear existing rows
            data.forEach(contact => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${contact.id}</td>
                    <td>${contact.name}</td>
                    <td>${contact.contact}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => {
            console.error("Error loading contacts:", err);
            document.getElementById('contactsMsg').textContent = 'Error loading contacts.';
        });
}

document.addEventListener('DOMContentLoaded', function() {
    fetchCertificates();
    loadBatchJobs();
    loadGpoZips();
    loadContacts(); // Ensure contacts are loaded when the page loads
});