import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';

export default function StyleGuidePage() {
  return (
    <main className="mx-auto max-w-4xl space-y-12 p-8 py-12">
      <header className="space-y-4">
        <p className="font-mono text-xs uppercase tracking-wider text-[color:var(--color-text-tertiary)]">
          Wave 0.5 — design system
        </p>
        <h1 className="text-5xl">Портал НУГ</h1>
        <p className="max-w-2xl text-lg leading-relaxed text-[color:var(--color-text-secondary)]">
          AI-агенты для исследовательских задач НУГ &laquo;Цифровые технологии в математическом
          образовании&raquo;. Этот гайд показывает финализованную дизайн-систему, на которой строится
          весь интерфейс портала.
        </p>
      </header>

      <section className="space-y-6">
        <h2 className="text-3xl">Палитра</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {[
            { name: 'bg-primary', cls: 'bg-[color:var(--color-bg-primary)]', text: 'paper' },
            { name: 'bg-secondary', cls: 'bg-[color:var(--color-bg-secondary)]', text: 'card' },
            { name: 'bg-tertiary', cls: 'bg-[color:var(--color-bg-tertiary)]', text: 'hover' },
            { name: 'accent', cls: 'bg-[color:var(--color-accent)]', text: 'rust', light: true },
            { name: 'accent-hover', cls: 'bg-[color:var(--color-accent-hover)]', text: 'deep rust', light: true },
            { name: 'accent-soft', cls: 'bg-[color:var(--color-accent-soft)]', text: 'tint' },
            { name: 'success', cls: 'bg-[color:var(--color-success)]', text: 'moss', light: true },
            { name: 'warning', cls: 'bg-[color:var(--color-warning)]', text: 'amber', light: true },
            { name: 'error', cls: 'bg-[color:var(--color-error)]', text: 'firebrick', light: true },
            { name: 'info', cls: 'bg-[color:var(--color-info)]', text: 'navy', light: true },
            { name: 'border', cls: 'bg-[color:var(--color-border)]', text: 'taupe' },
            { name: 'border-strong', cls: 'bg-[color:var(--color-border-strong)]', text: 'taupe+' },
          ].map((c) => (
            <div
              key={c.name}
              className={`flex h-24 flex-col justify-end rounded-md border border-[color:var(--color-border)] p-3 ${c.cls}`}
            >
              <div className={c.light ? 'text-[color:var(--color-bg-primary)]' : 'text-[color:var(--color-text-primary)]'}>
                <div className="font-mono text-xs">{c.name}</div>
                <div className="text-xs opacity-70">{c.text}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-3xl">Типографика</h2>
        <div className="space-y-4 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] p-8">
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-[color:var(--color-text-tertiary)]">
              h1 / Source Serif 4 / 3.5rem
            </div>
            <h1 className="text-5xl">Цифровые технологии</h1>
          </div>
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-[color:var(--color-text-tertiary)]">
              h2 / Source Serif 4 / 2.25rem
            </div>
            <h2 className="text-3xl">Заголовок раздела</h2>
          </div>
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-[color:var(--color-text-tertiary)]">
              body / Inter / 1rem
            </div>
            <p className="text-base leading-relaxed">
              Тёплая editorial-вёрстка с засечной типографикой для заголовков и санс-серифом Inter
              для интерфейсного текста. Кириллица идёт первым классом — оба шрифта подгружаются
              через next/font c subset cyrillic. Лигатуры не подключены, но шрифт всё равно
              ощущается живым за счёт правильного межбуквенного.
            </p>
          </div>
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-[color:var(--color-text-tertiary)]">
              mono / JetBrains Mono / 0.875rem
            </div>
            <code className="font-mono text-sm">npm run dev → http://localhost:3000</code>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-3xl">Компоненты</h2>
        <Card>
          <CardHeader>
            <CardTitle>Карточка с формой</CardTitle>
            <CardDescription>
              Тонкий border + warm secondary background. Focus ring брендовый rust.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="email">Корпоративный email</Label>
                <Input id="email" type="email" placeholder="ivanov@mirea.ru" />
              </div>
              <div className="flex flex-wrap gap-3">
                <Button>Запустить агента</Button>
                <Button variant="outline">Открыть каталог</Button>
                <Button variant="ghost">Отменить</Button>
                <Button variant="destructive">Удалить</Button>
                <Button variant="link">Подробнее</Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge>queued</Badge>
                <Badge>running</Badge>
                <Badge>succeeded</Badge>
                <Badge>failed</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <footer className="border-t border-[color:var(--color-border)] pt-6">
        <p className="font-mono text-xs text-[color:var(--color-text-tertiary)]">
          Wave 0.5 закрыт. Wave 1 (T7-T10) добавит layouts, landing, login, register.
        </p>
      </footer>
    </main>
  );
}
