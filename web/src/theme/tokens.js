/**
 * The iHub design tokens, following Apache Superset's default theme (superset/config.py,
 * THEME_DEFAULT): teal primary, Inter, the same status colours and the same categorical
 * chart palette. One deliberate difference: corners are square (borderRadius 0).
 *
 * Used by Ant Design (ConfigProvider), ECharts (registered theme) and global.css.
 */

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
};

/** Superset's default categorical scheme ("SUPERSET_DEFAULT"), in its order. */
export const categorical = [
  '#1FA8C9', '#454E7C', '#5AC189', '#FF7F44', '#666666',
  '#E04355', '#FCC700', '#A868B7', '#3CCCCB', '#A38F79',
  '#8FD3E4', '#A1A6BD', '#ACE1C4', '#FEC0A1', '#B2B2B2',
  '#EFA1AA', '#FDE380', '#D3B3DA', '#9EE5E5', '#D1C6BC',
];

export const fontFamily = "var(--font-inter), Inter, Helvetica, Arial, sans-serif";

/** Ant Design theme (seed tokens only, as Ant Design recommends). */
export const antdTheme = {
  token: {
    colorPrimary: colors.primary,
    colorLink: colors.link,
    colorError: colors.error,
    colorWarning: colors.warning,
    colorSuccess: colors.success,
    colorInfo: colors.info,
    colorText: colors.text,
    colorTextSecondary: colors.textSecondary,
    colorBorder: colors.border,
    colorBorderSecondary: colors.split,
    colorBgLayout: colors.layout,
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
    Layout: { headerBg: colors.surface, headerHeight: 56, headerPadding: '0 24px', bodyBg: colors.layout },
    Menu: { horizontalItemSelectedColor: colors.primary, itemHeight: 56 },
    Card: { headerFontSize: 16 },
    Table: { headerBg: colors.surface, headerSplitColor: 'transparent', rowHoverBg: '#f4f9fb' },
    Tabs: { titleFontSize: 13 },
  },
};

/** ECharts theme with the same palette and font. */
export const echartsTheme = {
  color: categorical,
  backgroundColor: 'transparent',
  textStyle: { fontFamily: 'Inter, Helvetica, Arial, sans-serif', color: colors.text },
  title: { textStyle: { color: colors.text, fontWeight: 500 } },
  legend: { textStyle: { color: colors.text }, icon: 'circle', itemWidth: 10, itemHeight: 10 },
  tooltip: { borderRadius: 0, textStyle: { fontSize: 12 } },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#333333' } },
    axisTick: { show: false },
    axisLabel: { color: colors.textSecondary },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisLabel: { color: colors.textSecondary },
    splitLine: { lineStyle: { color: colors.split } },
  },
  bar: { itemStyle: { borderRadius: 0 } },
};
