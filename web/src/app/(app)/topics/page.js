import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import BarList from '@/components/ui/BarList';
import Card, { CardHeader } from '@/components/ui/Card';
import Grid from '@/components/ui/Grid';
import LinkList from '@/components/ui/LinkList';
import { readFilters } from '@/lib/filters-server';
import { formatNumber } from '@/lib/format';
import { loadTopics } from '@/services/research';

export const metadata = {
  title: 'Research topics',
  description: 'Research fields drawn from OpenAlex classifications. Topic counts can overlap.',
};

export default async function TopicsPage({ searchParams }) {
  const { field } = await searchParams;
  const data = await loadTopics(await readFilters(), Array.isArray(field) ? field[0] : field);
  const { selected } = data;

  return (
    <>
      <PageHeader title="Research topics" />

      <Grid variant="main-aside" start>
        <Card aria-labelledby="themes-title">
          <CardHeader
            id="themes-title"
            title="Research themes"
            subtitle="Fields from OpenAlex classifications · counts may overlap"
          />
          {data.themes.length ? (
            <BarList items={data.themes} max={data.max} spacious />
          ) : (
            <p className="text-muted">No classified publications in this period.</p>
          )}
        </Card>

        <Card aria-labelledby="detail-title">
          <CardHeader id="detail-title" title="Topic detail" subtitle={selected?.field ?? 'No theme'} className="mb-32" />
          {selected && (
            <>
              <p className="big-figure big-figure--xl">{formatNumber(selected.publications)}</p>
              <p className="text-muted mt-8">outputs in this field</p>
              <h3 className="subhead--plain mt-40 text-md">Busiest topics in this field</h3>
              <div className="mt-20">
                <LinkList
                  roomy
                  items={selected.topics.map((topic) => ({
                    label: topic.name,
                    children: (
                      <span>
                        {topic.name} · {formatNumber(topic.publications)}
                      </span>
                    ),
                  }))}
                />
              </div>
              <p className="mt-40">
                <Link href="/publications">View publications →</Link>
              </p>
            </>
          )}
        </Card>
      </Grid>

      <Card className="mt-24" aria-labelledby="interpret-title">
        <h2 className="card__title" id="interpret-title">
          Topic interpretation
        </h2>
        <h3 className="subhead--lg mt-40">One output can contribute to several themes.</h3>
        <p className="text-muted mt-12">
          Topic totals are not additive. Labels come from OpenAlex classifications rather than an assessment of
          research quality, and only publications found in OpenAlex have topics.
        </p>
        <p className="mt-32">
          <Link href="/coverage">Publications that are not in OpenAlex have no topic. See source coverage.</Link>
        </p>
      </Card>
    </>
  );
}
