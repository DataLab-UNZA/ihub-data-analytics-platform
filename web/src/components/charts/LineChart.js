import Link from 'next/link';
import { formatNumber } from '@/lib/format';

const WIDTH = 700;
const HEIGHT = 180;
const PAD = { left: 36, right: 12, top: 8, bottom: 24 };

function tickLabel(value) {
  return value >= 1000 ? `${value / 1000}k` : String(value);
}

/**
 * Line-and-area chart rendered as inline SVG on the server.
 * Every point links to the matching record list, and the same data is
 * available as a visually hidden table for assistive technology.
 *
 * @param {string} id        Unique id (used for the gradient definition).
 * @param {string} caption   Accessible name and table caption.
 * @param {Array<{label: string, value: number}>} data Points, oldest first.
 * @param {number} max       Top of the y axis.
 * @param {number} step      Gridline spacing.
 * @param {string} drillHref Base URL; "?year=<label>" is appended per point.
 */
export default function LineChart({ id, caption, data, max = 3000, step = 1000, drillHref }) {
  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const last = data.length - 1;
  // Up to 12 points keep the design's every-other-year labels; longer series are thinned.
  const stride = data.length <= 12 ? 2 : Math.ceil(data.length / 9);

  // A single point sits in the middle of the plot instead of dividing by zero.
  const x = (index) => (last === 0 ? PAD.left + plotWidth / 2 : PAD.left + (index * plotWidth) / last);
  const y = (value) => PAD.top + plotHeight - (value / max) * plotHeight;

  const gridValues = [];
  for (let value = 0; value <= max; value += step) {
    gridValues.push(value);
  }

  const line = data
    .map((point, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)} ${y(point.value).toFixed(1)}`)
    .join(' ');
  const area = `${line} L${x(last)} ${y(0)} L${x(0)} ${y(0)} Z`;
  const gradientId = `${id}-fill`;

  return (
    <figure className="chart">
      <svg
        className="chart__svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="group"
        aria-label={`${caption}. Data is also available in the table below.`}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#27bedb" stopOpacity="0.35" />
            <stop offset="1" stopColor="#27bedb" stopOpacity="0" />
          </linearGradient>
        </defs>

        {gridValues.map((value) => (
          <g key={value}>
            <line className="chart__grid" x1={PAD.left} x2={WIDTH - PAD.right} y1={y(value)} y2={y(value)} />
            <text className="chart__label" x={PAD.left - 10} y={y(value) + 4} textAnchor="end">
              {tickLabel(value)}
            </text>
          </g>
        ))}

        <path d={area} fill={`url(#${gradientId})`} />
        <path className="chart__line" d={line} />

        {data.map((point, index) => {
          const showLabel = index === 0 || (index >= stride && (last - index) % stride === 0);
          return showLabel ? (
            <text className="chart__label" key={point.label} x={x(index)} y={HEIGHT - 4} textAnchor="middle">
              {point.label}
            </text>
          ) : null;
        })}

        {data.map((point, index) => (
          <Link
            className="chart__point"
            key={point.label}
            href={drillHref ? `${drillHref}?year=${encodeURIComponent(point.label)}` : '#'}
            aria-label={`${point.label}: ${formatNumber(point.value)} outputs`}
          >
            <circle className="chart__hit" cx={x(index)} cy={y(point.value)} r="10" />
            <circle className="chart__dot" cx={x(index)} cy={y(point.value)} r="4" />
          </Link>
        ))}
      </svg>

      <table className="sr-only">
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Year</th>
            <th scope="col">Outputs</th>
          </tr>
        </thead>
        <tbody>
          {data.map((point) => (
            <tr key={point.label}>
              <td>{point.label}</td>
              <td>{point.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
