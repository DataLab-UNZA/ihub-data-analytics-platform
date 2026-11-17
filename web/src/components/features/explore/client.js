/** Browser-side calls to the API through the /bff proxy (the token never reaches the browser). */

export async function bff(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/bff/${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  });
  if (response.status === 401) {
    // A full page load on purpose: the sign-in proxy must run again for an expired session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
    throw new Error('Your session has ended. Sign in again.');
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = Array.isArray(data?.detail) ? data.detail.map((d) => d.msg).join('; ') : data?.detail;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}

/** Saves a Blob as a file. */
export function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** The query body for /api/explore/* from Explore's form state. */
export function querySpec(form) {
  return {
    dataset: form.dataset,
    metrics: form.metrics,
    groupby: form.groupby,
    filters: form.filters
      .filter((f) => f.column && f.op)
      .map((f) => ({ column: f.column, op: f.op, value: f.value })),
    year_from: form.yearFrom ?? null,
    year_to: form.yearTo ?? null,
    series_limit: form.seriesLimit ?? null,
    order_desc: form.orderDesc,
    row_limit: form.rowLimit,
  };
}

/** Explore's form state from a saved chart's params (the inverse of querySpec). */
export function formFromParams(params, viz, options) {
  return {
    dataset: params.dataset,
    viz,
    metrics: params.metrics ?? [],
    groupby: params.groupby ?? [],
    filters: (params.filters ?? []).map((f, i) => ({ ...f, id: `f${i}` })),
    yearFrom: params.year_from ?? null,
    yearTo: params.year_to ?? null,
    seriesLimit: params.series_limit ?? null,
    orderDesc: params.order_desc ?? true,
    rowLimit: params.row_limit ?? 1000,
    options: options ?? {},
  };
}

export function metricKey(metric) {
  return typeof metric === 'string' ? metric : `${metric.aggregate}(${metric.column})`;
}
