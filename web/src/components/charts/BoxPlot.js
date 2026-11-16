const WIDTH = 720;
const ORIGIN = 226; // x of the value 0 whisker end
const PER_UNIT = 7.5; // pixels per output
const ROW_HEIGHT = 64;
const BOX_HEIGHT = 26;
const TICKS = [0, 10, 20, 30, 40];

const x = (value) => ORIGIN + value * PER_UNIT;

/**
 * Horizontal box plot: whiskers show the full range, the box the interquartile
 * range and the vertical line the median. No individual names are shown.
 *
 * @param {Array<{label: string, tone: 'accent'|'teal'|'blue', min: number, q1: number,
 *   median: number, q3: number, max: number}>} rows
 */
export default function BoxPlot({ title, description, tableCaption, rows }) {
  const height = rows.length * ROW_HEIGHT + 48;
  const axisY = height - 21;

  return (
    <figure>
      <svg className="chart__svg" viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-labelledby="box-title box-desc">
        <title id="box-title">{title}</title>
        <desc id="box-desc">{description}</desc>

        {rows.map((row, index) => (
          <text className="boxplot__row-label" key={row.label} x="0" y={index * ROW_HEIGHT + 37}>
            {row.label}
          </text>
        ))}
        {TICKS.map((tick) => (
          <text className="chart__label" key={tick} x={x(tick) + (tick === 0 ? 6 : 0)} y={axisY} textAnchor="middle">
            {tick === 40 ? '40+' : tick}
          </text>
        ))}

        {rows.map((row, index) => {
          const centre = index * ROW_HEIGHT + 32;
          const top = centre - BOX_HEIGHT / 2;
          return (
            <g key={row.label}>
              <line className="boxplot__whisker" x1={x(row.min)} x2={x(row.max)} y1={centre} y2={centre} />
              <rect
                className={`boxplot__box--${row.tone}`}
                x={x(row.q1)}
                y={top}
                width={x(row.q3) - x(row.q1)}
                height={BOX_HEIGHT}
                rx="2"
              />
              <line className="boxplot__median" x1={x(row.median)} x2={x(row.median)} y1={top} y2={top + BOX_HEIGHT} />
            </g>
          );
        })}
      </svg>

      <table className="sr-only">
        <caption>{tableCaption}</caption>
        <thead>
          <tr>
            <th scope="col">Unit</th>
            <th scope="col">Minimum</th>
            <th scope="col">Lower quartile</th>
            <th scope="col">Median</th>
            <th scope="col">Upper quartile</th>
            <th scope="col">Maximum</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>{row.min}</td>
              <td>{Math.round(row.q1)}</td>
              <td>{Math.round(row.median)}</td>
              <td>{Math.round(row.q3)}</td>
              <td>{Math.round(row.max)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
