import Link from 'next/link';
import type { Route } from 'next';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const EXAMPLE_AGENTS = [
  {
    icon: '🎓',
    name: 'Эксперт конкурсных работ',
    description: 'Анализирует работы школьников по чек-листу и выдаёт экспертное заключение в Word.',
  },
  {
    icon: '🔬',
    name: 'Поиск научных статей',
    description: 'Ищет статьи по теме в arXiv, SemScholar, Crossref. Возвращает curated список с аннотациями.',
  },
  {
    icon: '✍️',
    name: 'Проверка академического стиля',
    description: 'Проверяет научную работу на соответствие академическому стилю и даёт правки.',
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="font-serif text-5xl tracking-tight md:text-6xl">
          Портал НУГ
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-[color:var(--color-text-secondary)]">
          AI-агенты для исследовательских задач научно-учебной группы
          «Цифровые технологии в математическом образовании». Запускай агентов
          без кода, без CLI, с результатом в один клик.
        </p>
        <div className="mt-10">
          <Button asChild size="lg">
            <Link href={'/login' as Route} className="no-underline">
              Войти
            </Link>
          </Button>
          <p className="mt-4 text-sm text-[color:var(--color-text-secondary)]">
            Доступ — по приглашению. Свяжись с админом НУГ.
          </p>
        </div>
      </section>

      {/* Examples */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <h2 className="mb-8 text-center font-serif text-3xl">Примеры агентов</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {EXAMPLE_AGENTS.map((agent) => (
            <Card key={agent.name}>
              <CardHeader>
                <div className="text-4xl">{agent.icon}</div>
                <CardTitle className="text-xl">{agent.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{agent.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[color:var(--color-border)] py-6 text-center text-sm text-[color:var(--color-text-secondary)]">
        НУГ «Цифровые технологии в математическом образовании», МИРЭА · 2026
      </footer>
    </div>
  );
}
