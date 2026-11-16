'use client';

import { useEffect, useState } from 'react';

function formatClock(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/**
 * Live countdown text.
 *
 * @param {number} seconds Starting value.
 * @param {string} template Text with a "{t}" placeholder, e.g. "Resend code in {t}s".
 * @param {'seconds'|'clock'} format How {t} is rendered.
 * @param {string} done Text shown when the countdown reaches zero.
 */
export default function Countdown({ seconds, template, format = 'seconds', done = '' }) {
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRemaining((current) => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  if (remaining <= 0) {
    return <span>{done}</span>;
  }
  const value = format === 'clock' ? formatClock(remaining) : String(remaining);
  return <span>{template.replace('{t}', value)}</span>;
}
