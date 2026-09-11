/**
 * app.js - Client-side interactivity for E-Power Web System
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Modal Helper Functions
  window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
    }
  };

  window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
    }
  };

  // Close modal when clicking on overlay background
  document.querySelectorAll('.modal-overlay, .win-modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('active');
      }
    });
  });

  // Close modal with ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active, .win-modal-overlay.active').forEach(modal => {
        modal.classList.remove('active');
      });
    }
  });

  // 2. Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });

  // 3. Dynamic Meter Reading Live Calculation & Anomaly Warning
  const meterSelect = document.getElementById('meterSelect');
  const prevReadingInput = document.getElementById('prevReadingInput');
  const currReadingInput = document.getElementById('currReadingInput');
  const usageCalcDisplay = document.getElementById('usageCalcDisplay');
  const alertWarningBox = document.getElementById('alertWarningBox');

  if (meterSelect && prevReadingInput && currReadingInput && usageCalcDisplay) {
    meterSelect.addEventListener('change', () => {
      const selectedOption = meterSelect.options[meterSelect.selectedIndex];
      const prev = selectedOption.getAttribute('data-latest-reading') || '0';
      prevReadingInput.value = prev;
      evaluateReading();
    });

    currReadingInput.addEventListener('input', evaluateReading);

    function evaluateReading() {
      const prev = parseFloat(prevReadingInput.value) || 0;
      const curr = parseFloat(currReadingInput.value) || 0;
      const total = curr - prev;

      if (!currReadingInput.value) {
        if (usageCalcDisplay) usageCalcDisplay.textContent = '0.00 kWh';
        if (alertWarningBox) alertWarningBox.style.display = 'none';
        return;
      }

      if (usageCalcDisplay) {
        usageCalcDisplay.textContent = `${total.toFixed(2)} kWh`;
      }

      if (alertWarningBox) {
        if (total < 0) {
          alertWarningBox.textContent = `⚠️ ព្រមាន៖ លេខថ្មី (${curr}) តូចជាងលេខចាស់ (${prev})! កុងទ័រមិនអាចថយក្រោយបានទេ។`;
          alertWarningBox.className = 'alert alert-danger';
          alertWarningBox.style.display = 'block';
        } else if (prev > 0 && total > (prev * 2.5)) {
          alertWarningBox.textContent = `⚠️ ព្រមាន៖ ការប្រើប្រាស់កើនឡើងខ្ពស់ខុសធម្មតា (${total.toFixed(1)} kWh)! សូមត្រួតពិនិត្យឡើងវិញ។`;
          alertWarningBox.className = 'alert alert-warning';
          alertWarningBox.style.display = 'block';
        } else {
          alertWarningBox.style.display = 'none';
        }
      }
    }
  }

  // 4. Invoices Filtering (Desktop, Tablet, and Mobile Responsive Cards)
  const invoiceFilterBtns = document.querySelectorAll('.invoice-filter-btn');
  const invoiceRows = document.querySelectorAll('.invoice-row');
  const invoiceCountEl = document.getElementById('invoiceCountDisplay');
  const noInvoicesRow = document.getElementById('noInvoicesRow');

  if (invoiceFilterBtns.length > 0 && invoiceRows.length > 0) {
    function applyInvoiceFilter(filterValue) {
      if (!filterValue) filterValue = 'all';
      let visibleCount = 0;

      // Update button active appearance
      invoiceFilterBtns.forEach(b => {
        const bFilter = b.getAttribute('data-filter') || 'all';
        if (bFilter.toLowerCase() === filterValue.toLowerCase()) {
          b.classList.remove('btn-secondary');
          b.classList.add('btn-primary');
        } else {
          b.classList.remove('btn-primary');
          b.classList.add('btn-secondary');
        }
      });

      // Filter each invoice row
      invoiceRows.forEach(row => {
        const status = (row.getAttribute('data-status') || '').trim();
        let shouldShow = false;
        const fLower = filterValue.toLowerCase();

        if (fLower === 'all') {
          shouldShow = true;
        } else if (fLower === 'unpaid') {
          shouldShow = (status === 'Unpaid' || status === 'Partially Paid');
        } else if (fLower === 'overdue') {
          shouldShow = (status === 'Overdue');
        } else if (fLower === 'paid') {
          shouldShow = (status === 'Paid');
        } else {
          shouldShow = (status.toLowerCase() === fLower);
        }

        if (shouldShow) {
          row.classList.remove('is-hidden');
          row.removeAttribute('hidden');
          row.style.removeProperty('display');
          visibleCount++;
        } else {
          row.classList.add('is-hidden');
          row.setAttribute('hidden', 'true');
          row.style.setProperty('display', 'none', 'important');
        }
      });

      // Update counter in heading
      if (invoiceCountEl) {
        invoiceCountEl.textContent = visibleCount;
      }

      // Show/hide empty state
      if (noInvoicesRow) {
        if (visibleCount === 0) {
          noInvoicesRow.classList.remove('is-hidden');
          noInvoicesRow.removeAttribute('hidden');
          noInvoicesRow.style.removeProperty('display');
        } else {
          noInvoicesRow.classList.add('is-hidden');
          noInvoicesRow.setAttribute('hidden', 'true');
          noInvoicesRow.style.setProperty('display', 'none', 'important');
        }
      }
    }

    invoiceFilterBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const filter = btn.getAttribute('data-filter') || 'all';
        applyInvoiceFilter(filter);
      });
    });

    // Check URL query parameter (e.g. ?status=Unpaid or ?filter=Overdue) on load
    const urlParams = new URLSearchParams(window.location.search);
    const initialFilter = urlParams.get('status') || urlParams.get('filter');
    if (initialFilter) {
      applyInvoiceFilter(initialFilter);
    }
  }

  // 5. Offline Meter Readings Queue & Sync Manager
  const offlineBanner = document.getElementById('offlineQueueBanner');
  const offlineCountEl = document.getElementById('offlineCount');
  const btnSync = document.getElementById('btnSyncOfflineReadings');
  const readingForm = document.getElementById('readingForm');

  function getOfflineQueue() {
    try {
      return JSON.parse(localStorage.getItem('epower_offline_readings') || '[]');
    } catch(e) {
      return [];
    }
  }

  function saveOfflineQueue(queue) {
    localStorage.setItem('epower_offline_readings', JSON.stringify(queue));
    updateOfflineBanner();
  }

  function updateOfflineBanner() {
    const queue = getOfflineQueue();
    if (offlineBanner && offlineCountEl) {
      if (queue.length > 0) {
        offlineBanner.style.display = 'flex';
        offlineCountEl.textContent = queue.length;
      } else {
        offlineBanner.style.display = 'none';
      }
    }
  }

  if (readingForm) {
    readingForm.addEventListener('submit', async (e) => {
      // If offline or network error, intercept and store in queue
      if (!navigator.onLine) {
        e.preventDefault();
        const formData = new FormData(readingForm);
        const entry = {
          meter_id: formData.get('meter_id'),
          current_reading: parseFloat(formData.get('current_reading')),
          previous_reading: parseFloat(formData.get('previous_reading')) || 0,
          reading_date: formData.get('reading_date') || new Date().toISOString().split('T')[0],
          billing_month: formData.get('billing_month'),
          pricing_policy: formData.get('pricing_policy') || 'flat',
          flat_rate: parseFloat(formData.get('flat_rate')) || 800.0,
          tier1_rate: parseFloat(formData.get('tier1_rate')) || 400.0,
          tier2_rate: parseFloat(formData.get('tier2_rate')) || 600.0,
          auto_generate_invoice: true
        };

        const queue = getOfflineQueue();
        queue.push(entry);
        saveOfflineQueue(queue);

        alert('📴 កំពុងស្ថិតក្នុងរបៀប Offline! ការកត់ត្រាត្រូវបានរក្សាទុកក្នុងទូរស័ព្ទ/កុំព្យូទ័រជាបណ្តោះអាសន្ន។ វានឹងត្រូវ Sync ស្វ័យប្រវត្តិពេលមានអ៊ីនធឺណិត ឬចុចប៊ូតុង "Sync Now"។');
        readingForm.reset();
      }
    });
  }

  if (btnSync) {
    btnSync.addEventListener('click', async () => {
      const queue = getOfflineQueue();
      if (queue.length === 0) return;

      btnSync.disabled = true;
      btnSync.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> កំពុង Sync...';

      try {
        const res = await fetch('/api/readings/bulk_sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(queue)
        });

        if (res.ok) {
          const result = await res.json();
          localStorage.removeItem('epower_offline_readings');
          updateOfflineBanner();
          alert(`✓ បានធ្វើសមកាលកម្ម ${result.synced_count} កំណត់ត្រាទៅកាន់ប្រព័ន្ធជោគជ័យ!`);
          window.location.reload();
        } else {
          alert('Sync បរាជ័យ សូមពិនិត្យការតភ្ជាប់ឡើងវិញ!');
        }
      } catch (err) {
        alert('មិនអាចភ្ជាប់ទៅកាន់ Server បានទេ មិនទាន់អាច Sync បាននៅឡើយ។');
      } finally {
        btnSync.disabled = false;
        btnSync.innerHTML = '<i class="fa-solid fa-rotate"></i> ធ្វើសមកាលកម្ម (Sync Now)';
      }
    });
  }

  updateOfflineBanner();
});

