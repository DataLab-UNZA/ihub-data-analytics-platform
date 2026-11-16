import Link from 'next/link';
import { cx } from '@/lib/format';

/**
 * Accessible data table with a visually hidden caption.
 *
 * Column definition:
 *   key        property to read from each row
 *   header     column heading
 *   rowHeader  render this column as <th scope="row">
 *   href       (row) => url; wraps the cell text in a link
 *   render     (row) => node; full control of the cell content
 *
 * @param {'roomy'|'compact'|'measures'} variant Row density or fixed layout.
 */
export default function DataTable({ caption, columns, rows, variant, id, className }) {
  return (
    <div className="table-wrap">
      <table className={cx('table', variant && `table--${variant}`, className)} id={id}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th scope="col" key={column.key}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.id ?? index}>
              {columns.map((column) => {
                const content = renderCell(column, row);
                return column.rowHeader ? (
                  <th scope="row" key={column.key}>
                    {content}
                  </th>
                ) : (
                  <td key={column.key}>{content}</td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderCell(column, row) {
  if (column.render) {
    return column.render(row);
  }
  const value = row[column.key];
  if (column.href) {
    return <Link href={column.href(row)}>{value}</Link>;
  }
  return value;
}
