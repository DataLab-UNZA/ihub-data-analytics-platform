'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Button from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Form';
import { cx } from '@/lib/format';

const COMMON_PASSWORDS = ['password', 'password123', '123456789012', 'qwertyuiop12', 'letmein12345', 'iloveyou1234'];

/** Password and confirmation fields with a live rules checklist. */
export default function CreatePasswordForm({ defaultPassword = '' }) {
  const [password, setPassword] = useState(defaultPassword);
  const [confirmation, setConfirmation] = useState(defaultPassword);
  const confirmRef = useRef(null);

  const longEnough = password.length >= 12;
  const notCommon = password.length > 0 && !COMMON_PASSWORDS.includes(password.toLowerCase());

  useEffect(() => {
    confirmRef.current?.setCustomValidity(
      confirmation && confirmation !== password ? 'Passwords do not match.' : '',
    );
  }, [password, confirmation]);

  return (
    <form className="auth-form" action="/login" method="get">
      {/* Lets password managers associate the new password with the account. */}
      <input type="text" name="username" autoComplete="username" defaultValue="" hidden readOnly />
      <Field id="new-password" label="New password">
        <Input
          id="new-password"
          name="new-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={12}
          autoComplete="new-password"
          aria-describedby="password-hint password-rules"
          required
        />
      </Field>
      <Field id="confirm-password" label="Confirm password">
        <Input
          id="confirm-password"
          name="confirm-password"
          type="password"
          ref={confirmRef}
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
          autoComplete="new-password"
          required
        />
      </Field>
      <ul className="rule-list" id="password-rules">
        <li className={cx(longEnough && 'is-valid')}>12+ characters</li>
        <li className={cx(notCommon && 'is-valid')}>Not a common password</li>
      </ul>
      <Button className="mt-12" type="submit">
        Reset password
      </Button>
      <p>
        <Link href="/login">Back to sign in</Link>
      </p>
    </form>
  );
}
