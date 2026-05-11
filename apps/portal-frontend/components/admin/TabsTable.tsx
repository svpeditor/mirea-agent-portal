'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { toast } from 'sonner';
import { Pencil, Trash, Plus } from 'lucide-react';

interface Tab {
  id: string;
  slug: string;
  name: string;
  order_idx: number;
  agents_count: number;
}

export function TabsTable({ tabs }: { tabs: Tab[] }) {
  const router = useRouter();
  const sorted = [...tabs].sort((a, b) => a.order_idx - b.order_idx);

  async function deleteTab(id: string, agentsCount: number) {
    if (agentsCount > 0) {
      toast.error(`У этого таба ${agentsCount} агентов — сначала перенеси их в другой таб.`);
      return;
    }
    if (!confirm('Удалить этот таб?')) return;
    try {
      await apiClient(`/api/admin/tabs/${id}`, { method: 'DELETE' });
      toast.success('Таб удалён');
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-[color:var(--color-border)]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-20">Порядок</TableHead>
              <TableHead>Название</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Агентов</TableHead>
              <TableHead className="text-right">Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((tab) => (
              <TableRow key={tab.id}>
                <TableCell className="font-mono">{tab.order_idx}</TableCell>
                <TableCell>{tab.name}</TableCell>
                <TableCell>
                  <code className="font-mono text-xs">{tab.slug}</code>
                </TableCell>
                <TableCell>{tab.agents_count}</TableCell>
                <TableCell className="text-right">
                  <EditTabDialog tab={tab} onSaved={() => router.refresh()} />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteTab(tab.id, tab.agents_count)}
                    aria-label="Удалить таб"
                  >
                    <Trash className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <CreateTabDialog onCreated={() => router.refresh()} />
    </div>
  );
}

function EditTabDialog({ tab, onSaved }: { tab: Tab; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(tab.name);
  const [slug, setSlug] = useState(tab.slug);
  const [orderIdx, setOrderIdx] = useState(String(tab.order_idx));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiClient(`/api/admin/tabs/${tab.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name, slug, order_idx: parseInt(orderIdx, 10) }),
      });
      toast.success('Таб обновлён');
      setOpen(false);
      onSaved();
    } catch (err) {
      toast.error(mapApiError(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Редактировать таб">
          <Pencil className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Редактировать таб</DialogTitle>
        </DialogHeader>
        <form onSubmit={save} className="space-y-3">
          <div>
            <Label htmlFor={`name-${tab.id}`}>Название</Label>
            <Input id={`name-${tab.id}`} value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor={`slug-${tab.id}`}>Slug</Label>
            <Input id={`slug-${tab.id}`} value={slug} onChange={(e) => setSlug(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor={`order-${tab.id}`}>Порядок</Label>
            <Input
              id={`order-${tab.id}`}
              type="number"
              value={orderIdx}
              onChange={(e) => setOrderIdx(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full">
            Сохранить
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CreateTabDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [orderIdx, setOrderIdx] = useState('100');

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiClient('/api/admin/tabs', {
        method: 'POST',
        body: JSON.stringify({ name, slug, order_idx: parseInt(orderIdx, 10) }),
      });
      toast.success('Таб создан');
      setOpen(false);
      setName('');
      setSlug('');
      setOrderIdx('100');
      onCreated();
    } catch (err) {
      toast.error(mapApiError(err));
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Создать таб
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Новый таб</DialogTitle>
        </DialogHeader>
        <form onSubmit={create} className="space-y-3">
          <div>
            <Label htmlFor="new-name">Название</Label>
            <Input id="new-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Учебная" required />
          </div>
          <div>
            <Label htmlFor="new-slug">Slug</Label>
            <Input id="new-slug" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="uchebnaya" required />
          </div>
          <div>
            <Label htmlFor="new-order">Порядок</Label>
            <Input
              id="new-order"
              type="number"
              value={orderIdx}
              onChange={(e) => setOrderIdx(e.target.value)}
              placeholder="100"
              required
            />
          </div>
          <Button type="submit" className="w-full">
            Создать
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
