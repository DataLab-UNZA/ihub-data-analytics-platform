'use client';

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { echartsTheme } from '@/theme/tokens';

let themeRegistered = false;
let worldMap = null;

function loadWorldMap() {
  if (!worldMap) {
    worldMap = fetch('/maps/world.json')
      .then((response) => response.json())
      .then((geo) => echarts.registerMap('world', geo));
  }
  return worldMap;
}

function needsWorldMap(option) {
  return Boolean(option?.series?.some?.((s) => s.type === 'map' && s.map === 'world'));
}

/**
 * An Apache ECharts chart with the iHub (Superset) theme. Resizes with its container and
 * loads the world map only when a chart needs it.
 *
 * @param {object} option An ECharts option (see src/lib/viz.js).
 * @param {number|string} height Height of the chart area.
 */
export default function EChart({ option, height = 360, ariaLabel }) {
  const element = useRef(null);
  const chart = useRef(null);

  useEffect(() => {
    if (!themeRegistered) {
      echarts.registerTheme('ihub', echartsTheme);
      themeRegistered = true;
    }
    const instance = echarts.init(element.current, 'ihub', { renderer: 'canvas' });
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(element.current);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const apply = () => {
      if (!cancelled && chart.current && option) chart.current.setOption(option, { notMerge: true });
    };
    if (needsWorldMap(option) && !echarts.getMap('world')) {
      loadWorldMap().then(apply);
    } else {
      apply();
    }
    if (!option) chart.current?.clear();
    return () => {
      cancelled = true;
    };
  }, [option]);

  return <div ref={element} className="echart" style={{ height }} role="img" aria-label={ariaLabel} />;
}
