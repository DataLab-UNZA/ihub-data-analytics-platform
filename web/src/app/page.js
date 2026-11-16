import Link from 'next/link';
import Card from '@/components/ui/Card';
import { SCREEN_GROUPS, screensInGroup } from '@/config/screens';

export const metadata = {
  title: 'Screen index',
  description: 'Index of every iHub Analytics front-end screen, grouped by area.',
};

/** Developer-facing index of every screen, generated from the screen registry. */
export default function HomePage() {
  return (
    <main className="doc" id="main">
      <header>
        <h1 className="doc__title">iHub Analytics · Screen index</h1>
        <p className="doc__lead">
          43 screens built with Next.js. Start at <Link href="/login">Sign in</Link>, or open any screen below. Numbers
          match the order of the supplied designs.
        </p>
      </header>

      <div className="index-grid">
        {SCREEN_GROUPS.map((group, index) => (
          <Card className="index-group" aria-labelledby={`group-${index}`} key={group}>
            <h2 className="card__title" id={`group-${index}`}>
              {group}
            </h2>
            <ul className="index-group__list">
              {screensInGroup(group).map((screen) => (
                <li key={screen.path}>
                  <Link href={screen.path}>
                    <span className="index-group__num">{String(screen.n).padStart(2, '0')}</span>
                    {screen.title}
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </main>
  );
}
