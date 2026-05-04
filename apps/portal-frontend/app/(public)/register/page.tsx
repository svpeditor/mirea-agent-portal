import { apiServer } from '@/lib/api/server';
import { ApiError } from '@/lib/api/types';
import { RegisterForm } from './RegisterForm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import type { Route } from 'next';
import { Button } from '@/components/ui/button';

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ invite?: string }>;
}) {
  const { invite } = await searchParams;

  if (!invite) {
    return (
      <ErrorCard
        title="Ссылка-приглашение не указана"
        description="Эта страница требует параметр ?invite=..."
      />
    );
  }

  let inviteInfo: { email: string } | null = null;
  try {
    inviteInfo = await apiServer<{ email: string }>(
      `/api/auth/invite-info?token=${encodeURIComponent(invite)}`,
    );
  } catch (err) {
    return (
      <ErrorCard
        title="Приглашение недействительно"
        description={
          err instanceof ApiError && err.body?.error?.code === 'invite_invalid'
            ? 'Срок действия приглашения истёк или оно уже использовано. Свяжись с админом за новым.'
            : 'Не удалось проверить ссылку-приглашение.'
        }
      />
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Регистрация</CardTitle>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Ты получил приглашение на email <strong>{inviteInfo.email}</strong>.
            Придумай пароль чтобы продолжить.
          </p>
        </CardHeader>
        <CardContent>
          <RegisterForm token={invite} email={inviteInfo.email} />
        </CardContent>
      </Card>
    </div>
  );
}

function ErrorCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-6 text-[color:var(--color-text-secondary)]">{description}</p>
          <Button asChild>
            <Link href={'/' as Route} className="no-underline">
              На главную
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
