import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL!;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD!;

test('admin видит usage с топами по юзерам/агентам/моделям', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(ADMIN_EMAIL);
  await page.getByLabel('Пароль').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Войти' }).click();

  await page.goto('/admin/usage');

  // KPI cards
  await expect(page.getByText('Всего стоит')).toBeVisible();
  await expect(page.getByText('Запросов')).toBeVisible();
  await expect(page.getByText('В среднем за запрос')).toBeVisible();

  // Топ-блоки
  await expect(page.getByText('Топ юзеров')).toBeVisible();
  await expect(page.getByText('Топ агентов')).toBeVisible();
  await expect(page.getByText('Топ моделей')).toBeVisible();

  // Agent filter присутствует
  await expect(page.getByLabel(/Фильтр по агенту/i)).toBeVisible();
});
