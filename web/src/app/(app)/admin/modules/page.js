import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Grid from '@/components/ui/Grid';
import { modules } from '@/data/admin';

export const metadata = {
  title: 'Modules',
  description: 'Enable the capabilities your organisation needs. Every module shares one hierarchy and role model.',
};

export default function ModulesPage() {
  return (
    <>
      <PageHeader title="Modules" />

      <Card className="mb-24" aria-labelledby="hub-title">
        <h2 className="card__title" id="hub-title">
          One hub, adaptable modules
        </h2>
        <p className="card__sub">
          Enable the capabilities your organisation needs. Each module uses the same hierarchy and role model.
        </p>
      </Card>

      <Grid variant="thirds">
        {modules.map((module) => (
          <Card as="article" className="module" aria-labelledby={`mod-${module.id}`} key={module.id}>
            <header>
              <h2 className="card__title" id={`mod-${module.id}`}>
                {module.title}
              </h2>
              <p className="module__state">{module.state}</p>
            </header>
            <p className="module__body">{module.body}</p>
            <p className={module.footHref ? 'module__foot' : 'module__foot text-muted'}>
              {module.footHref ? <Link href={module.footHref}>{module.foot}</Link> : module.foot}
            </p>
            {module.href ? (
              <Button href={module.href} block>
                {module.action}
                <span className="sr-only">: {module.title}</span>
              </Button>
            ) : (
              <Button block disabled>
                {module.action}
              </Button>
            )}
          </Card>
        ))}
      </Grid>

      <p className="text-muted mb-24 text-md">
        Research remains usable when staff denominators are unavailable. Missing per-staff and per-FTE measures display
        Unknown.
      </p>
    </>
  );
}
