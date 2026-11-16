'use client';

import Button from '@/components/ui/Button';
import { useFilters } from '@/context/filters-context';

/** Resets every global filter. */
export default function ClearFiltersButton({ children = 'Clear filters', ...props }) {
  const { resetFilters } = useFilters();
  return (
    <Button onClick={() => resetFilters()} {...props}>
      {children}
    </Button>
  );
}
