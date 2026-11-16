'use client';

import Button from '@/components/ui/Button';
import { downloadCsv, tableToCsv } from '@/lib/csv';

/**
 * Downloads the rendered table with the given id as a CSV file.
 *
 * @param {string} tableId Id of the <table> to export.
 * @param {string} filename Name of the downloaded file.
 */
export default function ExportCsvButton({ tableId, filename = 'export.csv', children = 'CSV' }) {
  const handleClick = () => {
    const table = document.getElementById(tableId);
    if (table) {
      downloadCsv(tableToCsv(table), filename);
    }
  };

  return (
    <Button variant="secondary" size="sm" onClick={handleClick}>
      {children}
    </Button>
  );
}
