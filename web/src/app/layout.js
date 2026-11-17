import { AntdRegistry } from '@ant-design/nextjs-registry';
import { Inter, Playfair_Display, Roboto } from 'next/font/google';
import Providers from '@/theme/Providers';
import '@/styles/global.css';

// Inter is Apache Superset's typeface; Playfair Display is kept for the sign-in heading.
const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const playfair = Playfair_Display({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-playfair',
  display: 'swap',
});

const roboto = Roboto({
  subsets: ['latin'],
  weight: ['300', '400', '500', '700'],
  variable: '--font-roboto',
  display: 'swap',
});

export const metadata = {
  title: {
    default: 'iHub Analytics',
    template: '%s · iHub Analytics',
  },
  description: 'One trusted view of research output at the University of Zambia.',
  icons: { icon: '/img/favicon.svg' },
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en-GB" className={`${inter.variable} ${playfair.variable} ${roboto.variable}`}>
      <body>
        <AntdRegistry>
          <Providers>{children}</Providers>
        </AntdRegistry>
      </body>
    </html>
  );
}
