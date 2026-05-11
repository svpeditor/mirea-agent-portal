import { test, expect } from '@playwright/test';
import { loginViaApi } from './helpers/auth';
import { createInvite } from './fixtures/seed';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL!;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD!;

test('register-by-invite → auto-login → видим /agents → logout → защита', async ({ page, request }) => {
  // Setup: admin создаёт invite
  const adminCookie = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);
  const newEmail = `e2e-${Date.now()}@test.local`;
  const inviteToken = await createInvite(request, adminCookie, newEmail);

  // Юзер открывает register
  await page.goto(`/register?invite=${inviteToken}`);
  await expect(page.getByText(newEmail)).toBeVisible();

  // Заполняет форму
  await page.getByLabel('Пароль (от 12 символов)').fill('VerySecure12345!');
  await page.getByLabel('Повтори пароль').fill('VerySecure12345!');
  await page.getByRole('button', { name: 'Создать аккаунт' }).click();

  // → /agents
  await expect(page).toHaveURL(/\/agents/);

  // Logout через avatar dropdown
  await page.getByRole('button').filter({ hasText: /^[A-Z]{2}$/ }).first().click();
  await page.getByRole('menuitem', { name: 'Выйти' }).click();

  // Попытка зайти на /agents → /login
  await page.goto('/agents');
  await expect(page).toHaveURL(/\/login/);
});
