import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL!;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD!;

test('admin создаёт invite → ссылка → новый юзер регистрируется', async ({ page, context }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(ADMIN_EMAIL);
  await page.getByLabel('Пароль').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Войти' }).click();

  await page.goto('/admin/users');
  await page.getByRole('button', { name: 'Создать инвайт' }).click();

  const newEmail = `e2e-invite-${Date.now()}@test.local`;
  await page.getByLabel('Email').fill(newEmail);
  await page.getByRole('button', { name: 'Создать ссылку' }).click();

  // Ссылка появилась в readonly input
  const linkInput = await page.locator('input[readonly]').inputValue();
  expect(linkInput).toMatch(/\/register\?invite=/);

  // Новый юзер регистрируется
  const userPage = await context.newPage();
  await userPage.goto(linkInput);
  await userPage.getByLabel('Пароль (от 12 символов)').fill('VerySecure12345!');
  await userPage.getByLabel('Повтори пароль').fill('VerySecure12345!');
  await userPage.getByRole('button', { name: 'Создать аккаунт' }).click();
  await expect(userPage).toHaveURL(/\/agents/);
});
