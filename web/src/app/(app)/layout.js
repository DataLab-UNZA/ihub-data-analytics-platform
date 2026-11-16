import Shell from '@/components/layout/Shell';

/** Signed-in screens share the sidebar, top bar and global filters. */
export default function AppLayout({ children }) {
  return <Shell>{children}</Shell>;
}
