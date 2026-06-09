$(document).ready(function() {
    $('.alert-dismissible').delay(4000).slideUp(300);
    $('.select2-init').select2({ width: '100%' });
    $('[data-bs-toggle="tooltip"]').tooltip();
    $('input[type="date"]').each(function() {
        if (!this.value) {
            const today = new Date().toISOString().split('T')[0];
            if (!this.hasAttribute('min')) {
                this.setAttribute('min', today);
            }
        }
    });
    $('.table-responsive table').each(function() {
        if ($(this).find('tbody tr').length > 10) {
            $(this).before('<div class="p-2 small text-muted">Showing all ' + $(this).find('tbody tr').length + ' records</div>');
        }
    });
    $('#selectAll').on('change', function() {
        $('.select-item').prop('checked', this.checked);
    });
    $('[data-confirm]').on('click', function(e) {
        if (!confirm($(this).data('confirm') || 'Are you sure?')) {
            e.preventDefault();
        }
    });
});

function togglePassword(fieldId, btn) {
    const field = document.getElementById(fieldId);
    const icon = btn.querySelector('i');
    if (field.type === 'password') {
        field.type = 'text';
        icon.className = 'bi bi-eye-slash';
    } else {
        field.type = 'password';
        icon.className = 'bi bi-eye';
    }
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatCurrency(amount) {
    return '$' + parseFloat(amount || 0).toFixed(2);
}

function getStatusBadge(status) {
    const map = {
        'paid': 'success', 'completed': 'success', 'active': 'success',
        'scheduled': 'warning', 'pending': 'warning', 'partial': 'warning',
        'cancelled': 'danger', 'unpaid': 'danger', 'inactive': 'secondary',
        'discharged': 'secondary', 'no_show': 'dark', 'in_progress': 'info'
    };
    return `<span class="badge bg-${map[status] || 'secondary'}">${status}</span>`;
}

function searchPatient(query, callback) {
    if (query.length < 2) return;
    fetch('/receptionist/search-patients?q=' + encodeURIComponent(query))
        .then(r => r.json())
        .then(data => callback(data))
        .catch(() => {});
}

function printElement(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const win = window.open('', '', 'width=800,height=600');
    win.document.write('<html><head><title>Print</title>');
    win.document.write('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">');
    win.document.write('</head><body>' + el.innerHTML + '</body></html>');
    win.document.close();
    win.print();
}
