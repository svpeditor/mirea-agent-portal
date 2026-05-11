import type { Metadata } from 'next';
import { PT_Serif, PT_Sans, JetBrains_Mono, Old_Standard_TT } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';

// Russian academic publishing aesthetic.
// Body+display: PT Serif (Paratype, designed for Cyrillic).
// Wood-type masthead: Old Standard TT (19th-c. journal headings, Cyrillic-ready).
// UI body: PT Sans. Technical metadata: JetBrains Mono.
const ptSerif = PT_Serif({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '700'],
  style: ['normal', 'italic'],
  variable: '--font-pt-serif',
  display: 'swap',
});

const ptSans = PT_Sans({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '700'],
  style: ['normal', 'italic'],
  variable: '--font-pt-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '700'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});

const oldStandard = Old_Standard_TT({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '700'],
  style: ['normal', 'italic'],
  variable: '--font-old-standard',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Известия НУГ',
  description:
    'AI-агенты для исследовательских задач НУГ «Цифровые технологии в математическом образовании», МИРЭА',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="ru"
      className={`${ptSerif.variable} ${ptSans.variable} ${jetbrainsMono.variable} ${oldStandard.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
