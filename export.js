// Maco Equity Partners — research export utilities
// Walks the page DOM to collect KPI data + table data, serializes to CSV.

function macoExportCSV(reportTitle) {
  const rows = [];

  rows.push(['Maco Equity Partners Research']);
  rows.push([reportTitle || document.title]);
  rows.push(['Source: https://macoequitypartners.com']);
  rows.push(['Exported: ' + new Date().toISOString().split('T')[0]]);
  rows.push([]);

  // KPI band
  const kpis = document.querySelectorAll('.report-kpi-band .kpi');
  if (kpis.length) {
    rows.push(['Key Performance Indicators']);
    rows.push(['Metric', 'Value', 'Change']);
    kpis.forEach(k => {
      const label = textOf(k.querySelector('.kpi-label'));
      const value = textOf(k.querySelector('.kpi-value')).replace(/\s+/g, ' ');
      const delta = textOf(k.querySelector('.kpi-delta'));
      rows.push([label, value, delta]);
    });
    rows.push([]);
  }

  // Tables in report-section blocks
  document.querySelectorAll('.report-table').forEach(t => {
    const wrap = t.closest('.report-section');
    if (wrap) {
      const h3 = wrap.querySelector('h3');
      const h2 = wrap.querySelector('h2');
      const head = h3 || h2;
      if (head) rows.push([textOf(head).replace(/\.$/, '')]);
    }
    const headers = Array.from(t.querySelectorAll('thead th')).map(th => textOf(th));
    if (headers.length) rows.push(headers);
    t.querySelectorAll('tbody tr').forEach(tr => {
      rows.push(Array.from(tr.querySelectorAll('td')).map(td => textOf(td)));
    });
    rows.push([]);
  });

  // Deal cards
  const deals = document.querySelectorAll('.report-deal');
  if (deals.length) {
    rows.push(['Deal Spotlights']);
    rows.push(['Headline', 'Submarket', 'Price', '$/SF', 'Going-In Cap', 'Other']);
    deals.forEach(d => {
      const headline = textOf(d.querySelector('h4'));
      const submarket = textOf(d.querySelector('.submarket'));
      const stats = Array.from(d.querySelectorAll('.report-deal-stat .value')).map(v => textOf(v));
      rows.push([headline, submarket, ...stats]);
    });
    rows.push([]);
  }

  const csv = rows
    .map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','))
    .join('\n');

  // UTF-8 BOM so Excel handles em-dashes and unicode correctly
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (reportTitle || 'maco-report')
    .replace(/[^a-z0-9]+/gi, '_')
    .replace(/^_|_$/g, '')
    .toLowerCase() + '.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

function textOf(el) {
  return el ? el.textContent.trim() : '';
}
