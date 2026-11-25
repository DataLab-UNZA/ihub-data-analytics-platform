'use client';

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { useThemeMode } from '@/theme/Providers';
import { echartsThemeFor, optionForMode } from '@/theme/tokens';

let themesRegistered = false;
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
 * An Apache ECharts chart with the iHub (Superset) theme, light or dark to match the page.
 * Resizes with its container and loads the world map only when a chart needs it. A change of
 * mode re-creates the chart with the other theme.
 *
 * @param {object} option An ECharts option (see src/lib/viz.js).
 * @param {number|string} height Height of the chart area.
 * @param {(params: object) => void} onClick Called with the ECharts event when a mark is clicked.
 */
export default function EChart({ option, height = 360, ariaLabel, onClick }) {
  const { mode } = useThemeMode();
  const element = useRef(null);
  const chart = useRef(null);
  const clickHandler = useRef(onClick);
  useEffect(() => {
    clickHandler.current = onClick;
  }, [onClick]);

  useEffect(() => {
    if (!themesRegistered) {
      echarts.registerTheme('ihub', echartsThemeFor('light'));
      echarts.registerTheme('ihub-dark', echartsThemeFor('dark'));
      themesRegistered = true;
    }
    const instance = echarts.init(element.current, mode === 'dark' ? 'ihub-dark' : 'ihub', { renderer: 'canvas' });
    chart.current = instance;
    instance.on('click', (params) => clickHandler.current?.(params));
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(element.current);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, [mode]);

  useEffect(() => {
    let cancelled = false;
    const apply = () => {
      if (!cancelled && chart.current && option) chart.current.setOption(optionForMode(option, mode), { notMerge: true });
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
  }, [option, mode]);

  return <div ref={element} className="echart" style={{ height }} role="img" aria-label={ariaLabel} />;
}
