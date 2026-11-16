/** Chart scale helpers. */

/**
 * Picks a rounded axis maximum and gridline step for a series.
 * Example: niceScale(2750) is { max: 3000, step: 1000 }.
 */
export function niceScale(maxValue, targetTicks = 3) {
  if (!maxValue || maxValue <= 0) {
    return { max: 1, step: 1 };
  }
  const rough = maxValue / targetTicks;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const fraction = rough / magnitude;
  const multiplier = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
  const step = multiplier * magnitude;
  return { max: Math.ceil(maxValue / step) * step, step };
}
