import {
  AppstoreOutlined,
  AreaChartOutlined,
  BarChartOutlined,
  DotChartOutlined,
  GlobalOutlined,
  HeatMapOutlined,
  LineChartOutlined,
  NumberOutlined,
  PieChartOutlined,
  RadarChartOutlined,
  RiseOutlined,
  TableOutlined,
} from '@ant-design/icons';

/** One icon per chart type, shared by the chart builder and the ready-made charts. */
export const VIZ_ICONS = {
  table: <TableOutlined />,
  big_number: <NumberOutlined />,
  bar: <BarChartOutlined />,
  line: <LineChartOutlined />,
  area: <AreaChartOutlined />,
  pie: <PieChartOutlined />,
  treemap: <AppstoreOutlined />,
  heatmap: <HeatMapOutlined />,
  world_map: <GlobalOutlined />,
  combo: <RiseOutlined />,
  scatter: <DotChartOutlined />,
  sunburst: <RadarChartOutlined />,
};
