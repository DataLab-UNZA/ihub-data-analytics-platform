import { notFound } from 'next/navigation';
import PageHeader from '@/components/layout/PageHeader';
import SampleChartView from '@/components/features/explore/SampleChartView';
import { findSampleChart, sampleCharts } from '@/config/chart-modules';

export const metadata = {
  title: 'Sample chart',
  description: 'A sample chart for a module that is not connected yet.',
};

/** One sample chart (HR, student information or learning management), with made-up numbers. */
export default async function SampleChartPage({ params }) {
  const { id } = await params;
  const found = findSampleChart(id);
  if (!found) notFound();
  return (
    <>
      <PageHeader title="Explore" filters={false} />
      <SampleChartView chart={found.chart} chartModule={found.chartModule} related={sampleCharts(found.chartModule.key).filter((other) => other.id !== id)} />
    </>
  );
}
