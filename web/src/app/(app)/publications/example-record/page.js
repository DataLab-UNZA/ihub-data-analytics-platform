import { redirect } from 'next/navigation';
import { apiGet } from '@/lib/api';

export const metadata = {
  title: 'Publication record',
  description: 'Opens the most recent publication record.',
};

/** The screen index links here: it opens the newest, most cited publication in the mart. */
export default async function ExampleRecordPage() {
  const { rows } = await apiGet('/api/publications', { page_size: 1 });
  if (rows.length === 0) {
    redirect('/publications');
  }
  redirect(`/publications/${rows[0].publication_key}`);
}
