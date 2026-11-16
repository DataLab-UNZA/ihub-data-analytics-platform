import { cx } from '@/lib/format';

/**
 * Content area of an authentication screen: the white card plus the
 * "Need access?" line. The page frame (logo, backdrop, tagline) lives in
 * the (auth) route-group layout.
 *
 * @param {string} title   The page's <h1>.
 * @param {string} lead    Muted line under the title.
 * @param {boolean} center Centre the heading (sign-in screens).
 * @param {boolean} tall   Give the card the standard minimum height.
 */
export default function AuthPage({ title, lead, leadId, center = false, tall = false, headClassName, children }) {
  return (
    <main className="auth__main" id="main">
      <section className={cx('auth-card', tall && 'auth-card--tall')} aria-labelledby="auth-title">
        <header className={cx('auth-card__head', center && 'auth-card__head--center', headClassName)}>
          <h1 className="auth-card__title" id="auth-title">
            {title}
          </h1>
          <p className="auth-card__lead" id={leadId}>
            {lead}
          </p>
        </header>
        {children}
      </section>
      <p className="auth__help">
        <a href="mailto:admin@unza.zm">Need access? Contact your workspace admin</a>
      </p>
    </main>
  );
}
