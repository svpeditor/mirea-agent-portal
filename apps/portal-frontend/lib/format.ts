import { formatDistanceToNow, format } from 'date-fns';
import { ru } from 'date-fns/locale';

export function formatRelativeTime(iso: string): string {
  return formatDistanceToNow(new Date(iso), { locale: ru, addSuffix: true });
}

export function formatDate(iso: string): string {
  return format(new Date(iso), 'd MMM yyyy, HH:mm', { locale: ru });
}

export function formatDuration(startIso: string, endIso: string | null): string {
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const sec = Math.floor((end - start) / 1000);
  if (sec < 60) return `${sec}с`;
  if (sec < 3600) return `${Math.floor(sec / 60)}м ${sec % 60}с`;
  return `${Math.floor(sec / 3600)}ч ${Math.floor((sec % 3600) / 60)}м`;
}

export function formatCurrency(usdString: string): string {
  const n = parseFloat(usdString);
  if (Number.isNaN(n) || n === 0) return '—';
  if (n < 0.01) return `<$0.01`;
  return `$${n.toFixed(2)}`;
}
