import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import { Input } from '@/components/ui/Form';
import { searchResults } from '@/data/publications';

export const metadata = {
  title: 'Search results',
  description: 'Search results across publications, units and authorised members.',
};

const DEFAULT_QUERY = 'community health';

/** `searchParams` is a promise in the App Router. The query is echoed back into the form and heading. */
export default async function SearchPage({ searchParams }) {
  const params = await searchParams;
  const query = (Array.isArray(params.q) ? params.q[0] : params.q) || DEFAULT_QUERY;

  return (
    <>
      <PageHeader title="Search results" />

      <Card className="mb-24" aria-labelledby="search-title">
        <CardHeader
          id="search-title"
          title="Search across your organisation"
          subtitle="Results use the global filters and your current permissions"
        />
        <form className="search-form" role="search" action="/search" method="get">
          <label className="sr-only" htmlFor="results-query">
            Search term
          </label>
          <Input
            className="search-form__input"
            id="results-query"
            type="search"
            name="q"
            defaultValue={query}
            key={query}
            autoComplete="off"
          />
          <Button size="md" type="submit">
            Search
          </Button>
        </form>
      </Card>

      <Card aria-labelledby="results-title">
        <CardHeader id="results-title" title={`Results for “${query}”`} className="mb-12">
          <ul className="result-counts" aria-label="Result groups">
            <li>Publications (24)</li>
            <li>Units (2)</li>
            <li>Members (3) · authorised results only</li>
          </ul>
        </CardHeader>

        <ol className="results">
          {searchResults.map((result) => (
            <li key={result.id}>
              <article>
                <p className="result__kind">{result.kind}</p>
                <Link className="result__title" href={result.href}>
                  {result.title}
                </Link>
                <p className="result__meta">{result.meta}</p>
              </article>
            </li>
          ))}
        </ol>
        <p className="card__foot">
          <Link href="/publications">View all publication results →</Link>
        </p>
      </Card>
    </>
  );
}
