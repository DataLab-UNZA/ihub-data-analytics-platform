/**
 * The iHub design tokens, following Apache Superset's default theme (superset/config.py,
 * THEME_DEFAULT): teal primary, Inter, the same status colours and the same categorical
 * chart palette. One deliberate difference: corners are square (borderRadius 0).
 *
 * Used by Ant Design (ConfigProvider), ECharts (registered theme) and global.css.
 * There are two modes, light and dark: global.css holds the matching CSS variables under
 * `:root` and `:root[data-theme='dark']`, and the functions below give Ant Design and ECharts
 * the same palette for the mode in use.
 */

import { theme as antdThemes } from 'antd';

export const colors = {
  primary: '#2893B3',
  link: '#2893B3',
  error: '#e04355',
  warning: '#fcc700',
  success: '#5ac189',
  info: '#66bcfe',
  text: '#333333',
  textSecondary: '#666666',
  textTertiary: '#879399',
  border: '#e0e0e0',
  split: '#f0f0f0',
  layout: '#f7f7f7',
  surface: '#ffffff',
  rowHover: '#f4f9fb',
  axis: '#333333',
};

/** The dark palette: the same teal and status colours, lifted where they sit on dark grey. */
export const darkColors = {
  primary: '#2893B3',
  link: '#4fb3d1',
  error: '#f0707f',
  warning: '#fcc700',
  success: '#5ac189',
  info: '#66bcfe',
  text: '#e6e6e6',
  textSecondary: '#a6a6a6',
  textTertiary: '#8c8c8c',
  border: '#383838',
  split: '#2a2a2a',
  layout: '#141414',
  surface: '#1f1f1f',
  rowHover: '#1d2b30',
  axis: '#8c8c8c',
};

const paletteFor = (mode) => (mode === 'dark' ? darkColors : colors);

/** Superset's default categorical scheme ("SUPERSET_DEFAULT"), in its order. */
export const categorical = [
  '#1FA8C9', '#454E7C', '#5AC189', '#FF7F44', '#666666',
  '#E04355', '#FCC700', '#A868B7', '#3CCCCB', '#A38F79',
  '#8FD3E4', '#A1A6BD', '#ACE1C4', '#FEC0A1', '#B2B2B2',
  '#EFA1AA', '#FDE380', '#D3B3DA', '#9EE5E5', '#D1C6BC',
];

/** The same scheme for dark mode, with the two greys and the navy lifted so they stay visible. */
export const categoricalDark = categorical.map(
  (colour) => ({ '#454E7C': '#7B86C2', '#666666': '#9E9E9E', '#B2B2B2': '#8A8A8A' })[colour] ?? colour,
);

/** The categorical scheme for a mode. */
export const categoricalFor = (mode) => (mode === 'dark' ? categoricalDark : categorical);

export const fontFamily = "var(--font-inter), Inter, Helvetica, Arial, sans-serif";

/** Ant Design theme for a mode (seed tokens only, as Ant Design recommends). */
export function antdThemeFor(mode = 'light') {
  const c = paletteFor(mode);
  return {
    algorithm: mode === 'dark' ? antdThemes.darkAlgorithm : antdThemes.defaultAlgorithm,
    token: {
      colorPrimary: c.primary,
      colorLink: c.link,
      colorError: c.error,
      colorWarning: c.warning,
      colorSuccess: c.success,
      colorInfo: c.info,
      colorText: c.text,
      colorTextSecondary: c.textSecondary,
      colorBorder: c.border,
      colorBorderSecondary: c.split,
      colorBgLayout: c.layout,
      colorBgContainer: c.surface,
      colorBgElevated: mode === 'dark' ? '#262626' : c.surface,
      fontFamily,
      fontSize: 14,
      borderRadius: 0,
      borderRadiusSM: 0,
      borderRadiusLG: 0,
      borderRadiusXS: 0,
      controlHeight: 32,
      wireframe: false,
    },
    components: {
      Tooltip: { fontSize: 12 },
      Layout: { headerBg: c.surface, headerHeight: 56, headerPadding: '0 24px', bodyBg: c.layout },
      Menu: { horizontalItemSelectedColor: c.primary, itemHeight: 56, itemBg: 'transparent', popupBg: mode === 'dark' ? '#262626' : c.surface },
      Card: { headerFontSize: 16 },
      Table: { headerBg: c.surface, headerSplitColor: 'transparent', rowHoverBg: c.rowHover },
      Tabs: { titleFontSize: 13 },
    },
  };
}

/** The light Ant Design theme (kept for code that does not switch modes). */
export const antdTheme = antdThemeFor('light');

/** ECharts theme for a mode, with the same palette and font. */
export function echartsThemeFor(mode = 'light') {
  const c = paletteFor(mode);
  const dark = mode === 'dark';
  return {
    color: categoricalFor(mode),
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'Inter, Helvetica, Arial, sans-serif', color: c.text },
    title: { textStyle: { color: c.text, fontWeight: 500 } },
    legend: { textStyle: { color: c.text }, icon: 'circle', itemWidth: 10, itemHeight: 10, pageTextStyle: { color: c.textSecondary } },
    tooltip: {
      borderRadius: 0,
      textStyle: { fontSize: 12, color: c.text },
      ...(dark ? { backgroundColor: '#262626', borderColor: c.border } : {}),
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: c.axis } },
      axisTick: { show: false },
      axisLabel: { color: c.textSecondary },
      splitLine: { show: false },
    },
    valueAxis: {
      axisLine: { show: false },
      axisLabel: { color: c.textSecondary },
      splitLine: { lineStyle: { color: c.split } },
    },
    timeAxis: { axisLabel: { color: c.textSecondary }, splitLine: { lineStyle: { color: c.split } } },
    visualMap: { textStyle: { color: c.textSecondary } },
    bar: { itemStyle: { borderRadius: 0 } },
    // ECharts outlines pie labels in a light colour, which smears them on a dark surface.
    pie: { label: { color: c.text, textBorderWidth: 0 }, labelLine: { lineStyle: { color: c.textSecondary } } },
  };
}

/** The light ECharts theme. */
export const echartsTheme = echartsThemeFor('light');

/*
 * Colours that chart options (src/lib/viz.js and others) set on series directly, so the
 * registered theme cannot change them. In dark mode they are swapped for their dark
 * counterparts: slice borders take the dark surface, the empty map grey gets darker and the
 * sequential scales run from dark to bright instead of light to dark.
 */
const DARK_OPTION_COLOURS = {
  '#fff': darkColors.surface,
  '#ffffff': darkColors.surface,
  '#e5e5e5': '#3a3a3a',
  '#e9f4f7': '#123a46',
  '#d6eef5': '#123a46',
  '#454e7c': '#8FD3E4',
};
const COLOUR_KEYS = new Set(['borderColor', 'areaColor']);

function swapColours(value) {
  if (Array.isArray(value)) return value.map(swapColours);
  if (value && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => {
        if (COLOUR_KEYS.has(key) && typeof item === 'string') {
          return [key, DARK_OPTION_COLOURS[item.toLowerCase()] ?? item];
        }
        if (key === 'inRange' && item && Array.isArray(item.color)) {
          return [key, { ...item, color: item.color.map((col) => DARK_OPTION_COLOURS[String(col).toLowerCase()] ?? col) }];
        }
        return [key, swapColours(item)];
      }),
    );
  }
  return value;
}

/** A chart option ready for a mode: unchanged in light mode, with light-only colours swapped in dark. */
export function optionForMode(option, mode) {
  return mode === 'dark' && option ? swapColours(option) : option;
}
