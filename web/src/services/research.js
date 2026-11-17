import { apiGet } from '@/lib/api';
import { countryName, mapPosition } from '@/lib/countries';
import { yearParams } from '@/lib/filters-server';
import { capitalise, formatNumber, formatShare } from '@/lib/format';
import { sourceCounts } from '@/lib/sources';

const TONES = [undefined, 'teal', 'blue'];
const tone = (index) => TONES[index % TONES.length];

export async function loadJournals(filters) {
  const data = await apiGet('/api/journals', { ...yearParams(filters), limit: 25 });
  const outputs = data.venues.reduce((sum, venue) => sum + venue.publications, 0);
  const oaOutputs = data.venues.reduce((sum, venue) => sum + venue.open_access_publications, 0);
  return {
    years: data.years,
    venuesInPeriod: data.venues_in_period,
    shown: data.venues.length,
    kpis: [
      { label: 'Venues', value: formatNumber(data.venues_in_period), note: 'Journals and other venues' },
      { label: 'Linked outputs', value: formatNumber(outputs), note: `In the ${data.venues.length} busiest venues` },
      {
        label: 'Open access',
        value: outputs ? formatShare(oaOutputs / outputs) : 'Unknown',
        note: 'Source-reported status',
      },
      { label: 'Coverage', value: 'Unknown', note: 'Expected corpus not supplied' },
    ],
    rows: data.venues.map((venue) => ({
      id: venue.venue,
      journal: venue.venue,
      outputs: formatNumber(venue.publications),
      oaShare: formatShare(venue.open_access_share),
      citations: formatNumber(venue.citations),
    })),
  };
}

export async function loadTopics(filters, selectedField) {
  const data = await apiGet('/api/topics', yearParams(filters));
  const fields = data.fields;
  const selected = fields.find((field) => field.field === selectedField) ?? fields[0] ?? null;
  return {
    years: data.years,
    max: fields[0]?.publications ?? 1,
    themes: fields.map((field, index) => ({
      label: field.field,
      value: field.publications,
      tone: tone(index),
      href: `/topics?field=${encodeURIComponent(field.field)}`,
    })),
    selected,
  };
}

export async function loadCollaboration(filters) {
  const data = await apiGet('/api/collaboration', yearParams(filters));
  const { summary } = data;
  const pins = data.countries
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
  return {
    years: data.years,
    kpis: [
      { label: 'Collaborative outputs', value: formatNumber(summary.international_publications), note: 'International co-authorship' },
      { label: 'Partner organisations', value: formatNumber(summary.partner_organisations), note: 'Source-linked affiliations' },
      { label: 'Countries', value: formatNumber(summary.countries), note: 'Known affiliations' },
      { label: 'Unknown country', value: formatNumber(summary.publications_with_unknown_country), note: 'Affiliation country missing' },
    ],
    pins,
    countries: data.countries.map((country) => ({
      id: country.country_code,
      country: countryName(country.country_code),
      outputs: formatNumber(country.publications),
    })),
    partners: data.partners.map((partner) => ({
      id: partner.name,
      partner: partner.name,
      country: partner.country_code ? countryName(partner.country_code) : 'Unknown',
      outputs: formatNumber(partner.publications),
    })),
  };
}

export async function loadCoverage(filters) {
  const data = await apiGet('/api/coverage', yearParams(filters));
  const kpiLabel = (source) => (source.code === 'dspace_oai' ? 'Repository' : source.code === 'ojs' ? 'UNZA journals' : source.name);
  return {
    years: data.years,
    publications: data.publications,
    kpis: data.sources.map((source) => ({
      label: kpiLabel(source),
      value: formatNumber(source.publications),
      note: `${formatShare(source.share)} of ${formatNumber(data.publications)} publications`,
    })),
    sourceBars: data.sources.map((source, index) => ({
      label: source.name,
      value: source.publications,
      tone: tone(index),
    })),
    gaps: data.gaps.map((gap) => ({
      ...gap,
      rows: gap.rows.map((row) => ({
        id: row.publication_key,
        key: row.publication_key,
        title: row.title,
        year: String(row.year),
        foundIn: row.sources || capitalise(row.type),
      })),
    })),
  };
}

export async function loadSources() {
  const data = await apiGet('/api/sources');
  return {
    lastRun: data.last_pipeline_run,
    publications: data.publications,
    rows: data.sources.map((source) => ({
      id: source.code,
      source: source.name,
      kind: capitalise(source.kind),
      publications: formatNumber(source.publications),
      share: formatShare(data.publications ? source.publications / data.publications : 0),
    })),
  };
}

/** Unit names the data service uses for the publications no school is credited with. */
const NOT_CREDITED = 'Not credited to a school';
const UNASSIGNED = 'Unassigned department';

const slug = (text) => text.toLowerCase().replace(/[^a-z0-9]+/g, '-');

/** School credit from the staff roster (ADR-012), shaped for the screen. School-level numbers only. */
function creditView(credit) {
  const { stats } = credit;
  const share = credit.total_publications ? credit.credited_by_roster / credit.total_publications : 0;
  return {
    coverage: {
      total: credit.total_publications,
      byRoster: credit.credited_by_roster,
      any: credit.credited_any,
      share: formatShare(share),
    },
    stats: {
      authors: stats.authors_considered,
      linked: stats.roster_linked,
      departmentOnly: stats.department_only,
      ambiguous: stats.ambiguous,
      staffMatched: stats.roster_staff_matched,
      headcount: stats.roster_headcount,
    },
    bars: credit.schools
      .filter((school) => school.roster_publications > 0)
      .map((school, index) => ({
        label: school.school,
        value: school.roster_publications,
        tone: [undefined, 'teal', 'blue'][index % 3],
      })),
    rows: credit.schools.map((school) => ({
      id: slug(school.school),
      school: school.school,
      roster: formatNumber(school.roster_publications),
      any: formatNumber(school.publications),
      authors: formatNumber(school.roster_authors),
      staff: `${formatNumber(school.staff_matched)} of ${formatNumber(school.staff_in_roster)}`,
    })),
  };
}

/** Tree of the university and its schools, credited through the staff roster. */
function rosterTree(credit, total, sources) {
  const view = creditView(credit);
  const first = Math.max(0, credit.schools.findIndex((school) => school.roster_publications > 0));
  const schools = credit.schools.map((school, index) => ({
    id: `school-${slug(school.school)}`,
    name: school.school,
    kind: 'Unit',
    outputs: formatNumber(school.roster_publications),
    count: school.roster_publications,
    unit: school.school,
    sources: sourceCounts(sources.sources, sources.by_unit[school.school]),
    childrenLabel: `${formatNumber(school.roster_authors)} authors matched`,
    selected: index === first,
    details: [
      ['Publications (staff roster)', formatNumber(school.roster_publications)],
      ['Including department evidence', formatNumber(school.publications)],
      ['Staff matched to an author', `${formatNumber(school.staff_matched)} of ${formatNumber(school.staff_in_roster)}`],
    ],
  }));
  const uncredited = Math.max(0, total - credit.credited_by_roster);
  schools.push({
    id: 'school-not-credited',
    name: 'Not credited to a school',
    kind: 'Unit',
    outputs: formatNumber(uncredited),
    count: uncredited,
    inPie: false, // the rest of the corpus, not a unit: it would dwarf every school
    unit: NOT_CREDITED,
    sources: sourceCounts(sources.sources, sources.by_unit[NOT_CREDITED]),
    childrenLabel: 'no author on the staff roster',
    details: [['Publications with no roster-linked school', formatNumber(uncredited)]],
  });
  return {
    id: 'unza',
    name: 'University of Zambia',
    kind: 'Organisation',
    outputs: formatNumber(total),
    count: total,
    unit: null,
    sources: sourceCounts(sources.sources, sources.all),
    childrenLabel: `${credit.schools.length} units`,
    expanded: true,
    details: [
      ['Credited to at least one school', `${formatNumber(credit.credited_by_roster)} (${view.coverage.share})`],
      ['Including department evidence', formatNumber(credit.credited_any)],
    ],
    children: schools,
  };
}

/** Tree of the university and its schools from department evidence (used when there is no roster). */
function departmentTree(data, sources) {
  const unitsBySchool = new Map();
  for (const unit of data.units) {
    const key = unit.school ?? unit.name;
    if (!unitsBySchool.has(key)) unitsBySchool.set(key, []);
    unitsBySchool.get(key).push(unit);
  }
  const defaultIndex = Math.max(0, data.schools.findIndex((school) => school.school !== 'Unassigned department'));
  const schools = data.schools.map((school, index) => {
    const children = (unitsBySchool.get(school.school) ?? [])
      .filter((unit) => unit.name !== school.school)
      .map((unit) => ({
        id: `unit-${slug(unit.name)}`,
        name: unit.name,
        kind: capitalise(unit.unit_type),
        outputs: formatNumber(unit.publications),
        count: unit.publications,
        unit: school.school, // lists exist per school, so a department links to its school
        sources: null,
        childrenLabel: '0 units',
      }));
    return {
      id: `school-${slug(school.school)}`,
      name: school.school,
      kind: 'Unit',
      outputs: formatNumber(school.publications),
      count: school.publications,
      inPie: school.school !== UNASSIGNED,
      unit: school.school,
      sources: sourceCounts(sources.sources, sources.by_unit[school.school]),
      childrenLabel: `${children.length} unit${children.length === 1 ? '' : 's'}`,
      expanded: index === defaultIndex,
      selected: index === defaultIndex,
      children,
    };
  });
  return {
    id: 'unza',
    name: 'University of Zambia',
    kind: 'Organisation',
    outputs: formatNumber(data.total_publications),
    count: data.total_publications,
    unit: null,
    sources: sourceCounts(sources.sources, sources.all),
    childrenLabel: `${schools.length} units`,
    expanded: true,
    children: schools,
  };
}

/**
 * Loads the organisation screen. With the private staff roster (ADR-012) schools are credited through
 * their authors; without it the screen shows the department-based counts.
 */
export async function loadOrganisation(filters) {
  const data = await apiGet('/api/organisation', yearParams(filters));
  const credit = data.school_credit ?? null;
  const sources = data.unit_sources;
  const tree = credit ? rosterTree(credit, data.total_publications, sources) : departmentTree(data, sources);
  return {
    years: data.years,
    tree,
    credit: credit ? creditView(credit) : null,
    schoolCount: tree.children.length,
    unitCount: data.units.length,
  };
}
