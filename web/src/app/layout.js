import { Poppins, Roboto_Condensed } from 'next/font/google';
import '@/styles/global.css';

const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-poppins',
  display: 'swap',
});

const robotoCondensed = Roboto_Condensed({
  subsets: ['latin'],
  weight: ['700'],
  variable: '--font-roboto-condensed',
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
    <html lang="en-GB" className={`${poppins.variable} ${robotoCondensed.variable}`}>
      <body>{children}</body>
    </html>
  );
}
