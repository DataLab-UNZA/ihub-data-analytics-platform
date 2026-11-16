/** CSV export helpers (client side, no dependencies). */

function csvCell(text) {
  const clean = text.replace(/\s+/g, ' ').trim();
  return /[",\n]/.test(clean) ? `"${clean.replace(/"/g, '""')}"` : clean;
}

/** Builds CSV text from the rows of a rendered <table>. */
export function tableToCsv(table) {
  const lines = Array.from(table.querySelectorAll('tr')).map((row) =>
    Array.from(row.cells)
      .map((cell) => csvCell(cell.textContent ?? ''))
      .join(','),
  );
  return lines.join('\r\n');
}

/** Triggers a browser download of `text` as a UTF-8 CSV file. */
export function downloadCsv(text, filename) {
  const blob = new Blob([`﻿${text}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
