'use client';

import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { App, ConfigProvider } from 'antd';
import enGB from 'antd/locale/en_GB';
import { THEME_COOKIE, THEME_COOKIE_MAX_AGE, themeMode } from './mode';
import { antdThemeFor } from './tokens';

const ThemeModeContext = createContext({ mode: 'light', setMode: () => {}, toggleMode: () => {} });

/** The colour mode in use and functions to change it. */
export const useThemeMode = () => useContext(ThemeModeContext);

/**
 * Ant Design theme (Superset tokens, square corners) and British English for every page, plus
 * the light or dark mode. `initialMode` comes from the cookie, read by the root layout. A change
 * of mode updates `data-theme` on <html> (for global.css), Ant Design and the cookie at once.
 */
export default function Providers({ children, initialMode = 'light' }) {
  const [mode, setModeState] = useState(themeMode(initialMode));

  const setMode = useCallback((next) => {
    const value = themeMode(next);
    setModeState(value);
    document.documentElement.dataset.theme = value;
    document.cookie = `${THEME_COOKIE}=${value}; path=/; max-age=${THEME_COOKIE_MAX_AGE}; samesite=lax`;
  }, []);

  const toggleMode = useCallback(() => setMode(mode === 'dark' ? 'light' : 'dark'), [mode, setMode]);
  const context = useMemo(() => ({ mode, setMode, toggleMode }), [mode, setMode, toggleMode]);
  const antdTheme = useMemo(() => antdThemeFor(mode), [mode]);

  return (
    <ThemeModeContext.Provider value={context}>
      <ConfigProvider theme={antdTheme} locale={enGB}>
        <App>{children}</App>
      </ConfigProvider>
    </ThemeModeContext.Provider>
  );
}
