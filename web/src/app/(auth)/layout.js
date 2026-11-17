/**
 * Frame shared by the sign-in screens: the form on the left, the image on the right
 * (hidden on small screens). Each page supplies its own <main> through <AuthPage>.
 */
export default function AuthLayout({ children }) {
  return (
    <div className="auth">
      <section className="auth__panel">
        <header className="auth__brand">
          <svg className="auth__mark" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="12" width="4" height="9" />
            <rect x="10" y="7" width="4" height="14" />
            <rect x="17" y="3" width="4" height="18" />
          </svg>
          <span className="auth__brand-name">iHub</span>
          <span className="auth__brand-tag">Analytics</span>
        </header>
        {children}
        <footer className="auth__tagline">University of Zambia · Research analytics</footer>
      </section>
      <aside className="auth__visual" aria-hidden="true">
        <div className="auth__visual-text">
          <p className="auth__visual-title">One trusted view.</p>
          <p className="auth__visual-lead">
            Research output from OpenAlex, ORCID, the institutional repository and UNZA journals, refreshed every week.
          </p>
        </div>
      </aside>
    </div>
  );
}
