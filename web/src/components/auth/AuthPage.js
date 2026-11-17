import { cx } from '@/lib/format';

/**
 * Content of a sign-in screen: heading, lead line and the page's form, centred in the
 * left panel of the (auth) layout.
 *
 * @param {string} title   The page's <h1>.
 * @param {string} lead    Muted line under the title.
 * @param {node}   footer  Optional line at the bottom of the form column.
 */
export default function AuthPage({ title, lead, leadId, headClassName, footer, children }) {
  return (
    <main className="auth__main" id="main">
      <section className="auth-card" aria-labelledby="auth-title">
        <header className={cx('auth-card__head', headClassName)}>
          <h1 className="auth-card__title" id="auth-title">
            {title}
          </h1>
          <p className="auth-card__lead" id={leadId}>
            {lead}
          </p>
        </header>
        {children}
      </section>
      {footer && <p className="auth__help">{footer}</p>}
    </main>
  );
}
