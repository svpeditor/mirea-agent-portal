import { test, expect } from '@playwright/test';

const TEST_EMAIL = process.env.E2E_USER_EMAIL!;
const TEST_PASSWORD = process.env.E2E_USER_PASSWORD!;
const ECHO_AGENT_SLUG = process.env.E2E_ECHO_AGENT_SLUG ?? 'echo';

test('запуск echo → видим events feed → terminal status', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(TEST_EMAIL);
  await page.getByLabel('Пароль').fill(TEST_PASSWORD);
  await page.getByRole('button', { name: 'Войти' }).click();

  await page.goto(`/agents/${ECHO_AGENT_SLUG}`);
  await page.getByRole('button', { name: 'Запустить агента' }).click();
  await expect(page).toHaveURL(/\/jobs\//);

  await expect(page.getByText('Агент запущен')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('Задача завершена успешно')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('Готово')).toBeVisible();
});
