import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL!;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD!;

test('admin создаёт agent version → видим building → ready', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(ADMIN_EMAIL);
  await page.getByLabel('Пароль').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Войти' }).click();

  await page.goto('/admin/agents');

  // Открыть drawer для первого агента
  await page.getByRole('row').nth(1).click();

  // Drawer открыт → создать новую версию
  await page.getByRole('button', { name: 'Создать новую' }).click();
  await page.getByLabel(/Git ref/).fill('main');
  await page.getByRole('button', { name: 'Запустить build' }).click();

  // Toast «Build запущен»
  await expect(page.getByText(/Build запущен/i)).toBeVisible({ timeout: 5_000 });

  // Видим building / queued
  await expect(page.getByText(/building|queued/)).toBeVisible({ timeout: 10_000 });

  // Ждём ready (до 5 минут — реальный docker build)
  await expect(page.getByText('ready').first()).toBeVisible({ timeout: 300_000 });
});
