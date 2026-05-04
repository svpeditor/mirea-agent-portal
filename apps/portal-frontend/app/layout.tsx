import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Портал НУГ',
  description: 'AI-агенты для исследовательских задач НУГ "Цифровые технологии в математическом образовании"',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
