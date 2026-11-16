/** Small formatting helpers shared by components. */

const number = new Intl.NumberFormat('en-GB');

export function formatNumber(value) {
  return number.format(value);
}

/** Joins class names, skipping falsy values. */
export function cx(...parts) {
  return parts.filter(Boolean).join(' ');
}

/** Formats a share from 0 to 1 as a percentage with one decimal place ("64.2%"). */
export function formatShare(share) {
  return `${(share * 100).toFixed(1)}%`;
}

/** "+8.2%" or "-3.1%" for the change from `previous` to `current`; null when it cannot be computed. */
export function percentChange(current, previous) {
  if (!previous) {
    return null;
  }
  const change = ((current - previous) / previous) * 100;
  return `${change >= 0 ? '+' : '−'}${Math.abs(change).toFixed(1)}%`;
}

/** Change in a share in percentage points ("+3.1 pp"). */
export function pointsChange(current, previous) {
  const points = (current - previous) * 100;
  return `${points >= 0 ? '+' : '−'}${Math.abs(points).toFixed(1)} pp`;
}

/** Title-cases the first letter of a label. */
export function capitalise(text) {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}
