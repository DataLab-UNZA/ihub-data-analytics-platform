import { apiGet } from '@/lib/api';
import { can } from '@/lib/permissions';
import { CHART_MODULES, chartHref, sampleCharts } from '@/config/chart-modules';

/**
 * The ready-made charts this visitor may see. The data-quality theme is for people who look
 * after the data (stewards and administrators), so others do not get it.
 */
export async function loadCatalogue(user) {
  const themes = await apiGet('/api/explore/guides');
  const steward = can(user, 'sources:manage') || can(user, 'quality:review');
  return themes.filter((theme) => !theme.admin_only || steward);
}

/** The values the simple filters offer: years, kinds of publication and schools. */
export async function loadFilterOptions() {
  const data = await apiGet('/api/filters');
  const years = [];
  for (let year = data.years.end; year >= data.years.start; year -= 1) years.push(year);
  return {
    years,
    types: data.types,
    schools: data.schools.filter((school) => school !== 'Not credited to a school'),
  };
}

/**
 * Explore's charts grouped by module (see src/config/chart-modules.js): each module with its
 * themes, and every guide with the `href` it opens at. Live modules take their themes from
 * the API; a sample module gets one theme with its sample charts.
 */
export async function loadModules(user) {
  const research = await loadCatalogue(user);
  return CHART_MODULES.map((chartModule) => {
    const themes =
      chartModule.status === 'live'
        ? research
        : [{ key: `${chartModule.key}-samples`, title: chartModule.theme, blurb: chartModule.blurb, guides: sampleCharts(chartModule.key) }];
    return {
      ...chartModule,
      themes: themes.map((theme) => ({
        ...theme,
        guides: theme.guides.map((guide) => ({ ...guide, href: chartHref(guide, chartModule) })),
      })),
    };
  });
}

/**
 * The charts the Charts page shows first, by module: the featured guides of each live module
 * (drawn from a live query in the browser) and the sample charts of the others (which carry
 * their result).
 */
export async function loadFeatured(user) {
  const modules = await loadModules(user);
  return modules
    .map((chartModule) => {
      const guides = chartModule.themes.flatMap((theme) => theme.guides);
      const charts =
        chartModule.status === 'live'
          ? (chartModule.featured ?? []).map((id) => guides.find((guide) => guide.id === id)).filter(Boolean)
          : guides.slice(0, 2);
      return { key: chartModule.key, title: chartModule.title, blurb: chartModule.blurb, status: chartModule.status, charts };
    })
    .filter((chartModule) => chartModule.charts.length > 0);
}
