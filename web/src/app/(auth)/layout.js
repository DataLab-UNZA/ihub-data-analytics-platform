/**
 * Frame shared by every authentication screen: backdrop, logo and tagline.
 * Each page supplies its own <main> through <AuthPage>.
 */
export default function AuthLayout({ children }) {
  return (
    <div className="auth">
      <div className="auth__frame">
        <header className="auth__brand">
          <span className="auth__brand-name">iHub</span>
          <span className="auth__brand-tag">Analytics</span>
        </header>
        {children}
        <footer className="auth__tagline">One trusted view. Refreshed weekly.</footer>
      </div>
    </div>
  );
}
