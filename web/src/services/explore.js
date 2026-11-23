import { apiGet } from '@/lib/api';
import { can } from '@/lib/permissions';

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
