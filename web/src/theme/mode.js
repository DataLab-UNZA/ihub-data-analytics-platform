/**
 * The colour mode (light or dark). The choice is kept in a cookie, so the server renders the
 * page in the right mode and there is no flash of the other one on load.
 */

export const THEME_COOKIE = 'ihub-theme';

/** A year, in seconds: the choice is remembered on this browser until it is changed. */
export const THEME_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

/** The mode from a cookie value: 'dark' only when asked for, otherwise 'light'. */
export const themeMode = (value) => (value === 'dark' ? 'dark' : 'light');
