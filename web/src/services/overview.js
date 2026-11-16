import { apiGet, apiTry } from '@/lib/api';
import { countryName, mapPosition } from '@/lib/countries';
import { yearParams } from '@/lib/filters-server';
import { formatNumber, formatShare, percentChange, pointsChange } from '@/lib/format';
import { niceScale } from '@/lib/scale';
import { formatRefreshed, isStale } from '@/lib/shell-data';

const SCHOOL_TONES = [undefined, 'teal', 'blue', undefined, 'teal'];

function changeNote(text, previousYears, tone) {
  return { note: `${text} vs ${previousYears.start}–${previousYears.end}`, tone };
}

function kpiChange(current, previous, previousYears) {
  const text = percentChange(current, previous);
  if (!previousYears || text === null) {
    return null;
  }
  return changeNote(text, previousYears, current >= previous ? 'positive' : 'negative');
}

/** Loads the overview from the API and shapes it for <OverviewDashboard>. */
export async function loadOverview(filters) {
  const [data, health] = await Promise.all([apiGet('/api/overview', yearParams(filters)), apiTry('/api/health')]);
  const { headline: now, previous_headline: before, previous_years: previousYears, years } = data;

  const fallbackNote = { note: `${years.start}–${years.end}`, tone: 'neutral' };
  const outputs = kpiChange(now.publications, before?.publications, previousYears) ?? fallbackNote;
  const citations = kpiChange(now.citations, before?.citations, previousYears) ?? fallbackNote;
  const oaChange =
    before && before.publications
      ? changeNote(
          pointsChange(now.open_access_share, before.open_access_share),
          previousYears,
          now.open_access_share >= before.open_access_share ? 'positive' : 'negative',
        )
      : fallbackNote;

  const kpis = [
    { label: 'Total outputs', value: formatNumber(now.publications), ...outputs },
    { label: 'Open access', value: formatShare(now.open_access_share), ...oaChange },
    { label: 'Citations', value: formatNumber(now.citations), ...citations },
    {
      label: 'Outputs per staff',
      value: 'Unknown',
      note: 'Staff baseline not connected',
      tone: 'neutral',
    },
  ].map(({ note, tone, ...kpi }) => ({ ...kpi, note, tone }));

  const series = data.per_year.map((row) => ({ label: String(row.year), value: row.publications }));
  const scale = niceScale(Math.max(...series.map((point) => point.value), 0));

  const topSchool = data.schools[0]?.publications ?? 1;
  const schools = data.schools.slice(0, 5).map((school, index) => ({
    label: school.school,
    value: school.publications,
    tone: SCHOOL_TONES[index],
  }));

  const venues = data.top_venues.slice(0, 4).map((venue) => ({
    id: venue.venue,
    journal: venue.venue,
    outputs: formatNumber(venue.publications),
  }));

  const pins = data.collaboration.countries
    .map((country) => {
      const position = mapPosition(country.country_code);
      if (!position) return null;
      const name = countryName(country.country_code);
      return {
        name,
        label: `${name}, ${formatNumber(country.publications)} co-authored outputs`,
        ...position,
        large: country.country_code === 'ZM',
      };
    })
    .filter(Boolean);

  const topPartner = data.collaboration.countries.find((country) => country.country_code !== 'ZM');
  const lastRun = health?.last_pipeline_run ?? null;

  return {
    years,
    kpis,
    series,
    scale,
    schools,
    schoolMax: topSchool,
    schoolCount: data.schools.length,
    venues,
    pins,
    topPartner: topPartner
      ? { name: countryName(topPartner.country_code), publications: topPartner.publications }
      : null,
    oaShare: now.open_access_share,
    oaChange: before && before.publications ? now.open_access_share - before.open_access_share : null,
    missingFromRepository: data.missing_from_repository,
    stale: { isStale: isStale(lastRun), lastRun: formatRefreshed(lastRun) },
  };
}
