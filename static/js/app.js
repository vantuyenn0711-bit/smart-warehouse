(() => {
  'use strict';
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const toggle = document.querySelector('[data-open-sidebar]');
  let previousFocus;
  function setSidebar(open) {
    if (!sidebar || !overlay) return;
    sidebar.classList.toggle('is-open', open);
    overlay.hidden = !open;
    toggle?.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
    if (open) { previousFocus = document.activeElement; sidebar.querySelector('[data-close-sidebar]')?.focus(); }
    else if (previousFocus) { previousFocus.focus(); previousFocus = null; }
  }
  toggle?.addEventListener('click', () => setSidebar(true));
  document.querySelector('[data-close-sidebar]')?.addEventListener('click', () => setSidebar(false));
  overlay?.addEventListener('click', () => setSidebar(false));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && sidebar?.classList.contains('is-open')) setSidebar(false);
    if (event.key === 'Tab' && sidebar?.classList.contains('is-open')) {
      const nodes = [...sidebar.querySelectorAll('a[href],button:not([disabled])')].filter(node => node.offsetParent !== null);
      if (event.shiftKey && document.activeElement === nodes[0]) { nodes.at(-1)?.focus(); event.preventDefault(); }
      if (!event.shiftKey && document.activeElement === nodes.at(-1)) { nodes[0]?.focus(); event.preventDefault(); }
    }
  });
  document.querySelectorAll('[data-dismiss]').forEach(button => button.addEventListener('click', () => button.closest('.notice')?.remove()));
  const offline = document.getElementById('offline-banner');
  const connection = () => { if (offline) offline.hidden = navigator.onLine; };
  window.addEventListener('offline', connection); window.addEventListener('online', connection); connection();
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', event => {
      if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
      if (form.method.toLowerCase() !== 'post') return;
      const submitter = event.submitter;
      if (form.dataset.submitting === 'true') { event.preventDefault(); return; }
      form.dataset.submitting = 'true';
      form.setAttribute('aria-busy', 'true');
      if (submitter) {
        submitter.dataset.originalHtml = submitter.innerHTML;
        submitter.innerHTML = '<span class="loading-spinner" aria-hidden="true"></span> Đang xử lý…';
        // Retain the clicked button's name/value in the POST body.
        window.setTimeout(() => { submitter.disabled = true; }, 0);
      }
    });
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[data-submitting]').forEach(form => { delete form.dataset.submitting; form.removeAttribute('aria-busy'); });
    document.querySelectorAll('[data-original-html]').forEach(button => { button.innerHTML = button.dataset.originalHtml; button.disabled = false; delete button.dataset.originalHtml; });
  });
  const formset = document.querySelector('[data-formset-prefix]');
  if (formset) {
    const prefix = formset.dataset.formsetPrefix;
    const total = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const template = document.getElementById('empty-item-template');
    const tbody = document.getElementById('document-items');
    const addButton = document.getElementById('add-item');
    function wireDelete(row) {
      row.querySelector('[data-remove-item]')?.addEventListener('click', () => {
        const checkbox = row.querySelector('input[name$="-DELETE"]');
        if (checkbox) checkbox.checked = true;
        row.hidden = true;
        row.querySelectorAll('input,select,textarea').forEach(input => { input.required = false; });
        addButton?.focus();
      });
    }
    tbody?.querySelectorAll('[data-item-row]').forEach(wireDelete);
    addButton?.addEventListener('click', () => {
      if (!total || !template || !tbody) return;
      const count = Number.parseInt(total.value, 10);
      if (count >= 100) { window.alert('Một phiếu tối đa 100 dòng sản phẩm.'); return; }
      tbody.insertAdjacentHTML('beforeend', template.innerHTML.replaceAll('__prefix__', String(count)));
      total.value = String(count + 1);
      const row = tbody.lastElementChild;
      wireDelete(row); row.querySelector('select,input:not([type="hidden"])')?.focus();
    });
  }
  document.body.addEventListener('htmx:responseError', showRequestError);
  document.body.addEventListener('htmx:sendError', showRequestError);
  function showRequestError() {
    const main = document.getElementById('main-content');
    if (!main || main.querySelector('[data-request-error]')) return;
    const notice = document.createElement('div');
    notice.className = 'notice notice-error';
    notice.dataset.requestError = 'true';
    notice.setAttribute('role', 'alert');
    notice.textContent = 'Chưa tải được dữ liệu. Kiểm tra kết nối rồi thử lại hoặc tải lại trang.';
    main.prepend(notice);
  }
  document.querySelector('[data-print]')?.addEventListener('click', () => window.print());
})();
