import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl space-y-8 p-8">
      <h1 className="text-4xl">Портал НУГ — UI components preview</h1>

      <Card>
        <CardHeader>
          <CardTitle>Карточка</CardTitle>
          <CardDescription>Тонкий border + paper фон</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="ivan@mirea.ru" />
            </div>
            <div className="flex gap-2">
              <Button>Primary action</Button>
              <Button variant="outline">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="destructive">Danger</Button>
            </div>
            <div className="flex gap-2">
              <Badge>queued</Badge>
              <Badge>running</Badge>
              <Badge>succeeded</Badge>
              <Badge>failed</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
