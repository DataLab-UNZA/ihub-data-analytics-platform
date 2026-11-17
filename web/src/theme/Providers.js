'use client';

import { App, ConfigProvider } from 'antd';
import enGB from 'antd/locale/en_GB';
import { antdTheme } from './tokens';

/** Ant Design theme (Superset tokens, square corners) and British English for every page. */
export default function Providers({ children }) {
  return (
    <ConfigProvider theme={antdTheme} locale={enGB}>
      <App>{children}</App>
    </ConfigProvider>
  );
}
