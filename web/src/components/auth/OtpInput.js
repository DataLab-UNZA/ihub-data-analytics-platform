'use client';

import { useRef, useState } from 'react';

const LENGTH = 6;

/**
 * Six single-digit inputs for a one-time code.
 * Supports auto-advance, backspace, arrow keys and pasting the whole code.
 *
 * @param {string} defaultValue Digits to prefill (design preview only).
 */
export default function OtpInput({ defaultValue = '' }) {
  const [digits, setDigits] = useState(() => Array.from({ length: LENGTH }, (_, i) => defaultValue[i] ?? ''));
  const refs = useRef([]);

  const focus = (index) => refs.current[Math.max(0, Math.min(LENGTH - 1, index))]?.focus();

  const update = (index, value) =>
    setDigits((current) => current.map((digit, i) => (i === index ? value : digit)));

  const handleChange = (index, event) => {
    const value = event.target.value.replace(/\D/g, '').slice(-1);
    update(index, value);
    if (value) focus(index + 1);
  };

  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !digits[index]) focus(index - 1);
    if (event.key === 'ArrowLeft') focus(index - 1);
    if (event.key === 'ArrowRight') focus(index + 1);
  };

  const handlePaste = (index, event) => {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '');
    if (!pasted) return;
    event.preventDefault();
    setDigits((current) => current.map((digit, i) => (i >= index && pasted[i - index] ? pasted[i - index] : digit)));
    focus(index + pasted.length);
  };

  return (
    <fieldset className="otp">
      <legend className="sr-only">6-digit verification code</legend>
      {digits.map((digit, index) => (
        <input
          className="otp__input"
          key={index}
          ref={(node) => {
            refs.current[index] = node;
          }}
          type="text"
          name={`code-${index + 1}`}
          inputMode="numeric"
          pattern="[0-9]"
          maxLength={1}
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          placeholder="–"
          aria-label={`Digit ${index + 1}`}
          value={digit}
          onChange={(event) => handleChange(index, event)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          onPaste={(event) => handlePaste(index, event)}
          required
        />
      ))}
    </fieldset>
  );
}
