import Link from 'next/link';
import HierarchyEditor from '@/components/features/admin/HierarchyEditor';
import PageHeader from '@/components/layout/PageHeader';
import Card from '@/components/ui/Card';

export const metadata = {
  title: 'Hierarchy & labels',
  description: 'Rename organisational levels so the interface matches how your organisation describes itself.',
};

export default function HierarchyPage() {
  return (
    <>
      <PageHeader title="Hierarchy & labels" />
      <HierarchyEditor />

      <Card aria-labelledby="structure-title">
        <h2 className="card__title" id="structure-title">
          Manage structure
        </h2>
        <p className="text-muted mt-32">
          13 schools · 77 departments · moves retain historical membership and require confirmation.
        </p>
        <p className="mt-24 inline-links">
          <Link href="/admin/hierarchy">Add unit</Link>
          <Link href="/admin/hierarchy">Move unit</Link>
          <Link href="/admin/hierarchy">Import hierarchy</Link>
        </p>
      </Card>
    </>
  );
}
