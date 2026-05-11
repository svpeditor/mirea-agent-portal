import { test, expect } from '@playwright/test';
import { loginViaApi, API_BASE_URL } from './helpers/auth';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL!;
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD!;
const USER_EMAIL = process.env.E2E_USER_EMAIL!;
const USER_PASSWORD = process.env.E2E_USER_PASSWORD!;
const LLM_AGENT_SLUG = process.env.E2E_LLM_AGENT_SLUG ?? 'echo-llm';

test('юзер с исчерпанной квотой → ошибка при запуске LLM-агента', async ({ page, request }) => {
  // Setup: admin задаёт юзеру микро-квоту через API
  const adminCookie = await loginViaApi(request, ADMIN_EMAIL, ADMIN_PASSWORD);

  const usersRes = await request.get(`${API_BASE_URL}/api/admin/users`, {
    headers: { Cookie: adminCookie },
  });
  const usersList = (await usersRes.json()) as { users: Array<{ id: string; email: string }> };
  const targetUser = usersList.users.find((u) => u.email === USER_EMAIL);
  if (!targetUser) {
    test.skip(true, `User ${USER_EMAIL} not found in seed`);
    return;
  }

  await request.patch(`${API_BASE_URL}/api/admin/users/${targetUser.id}/quota`, {
    headers: { Cookie: adminCookie },
    data: { monthly_limit_usd: '0.0001', per_job_cap_usd: '0.0001' },
  });

  // Юзер логинится и пытается запустить LLM-агента
  await page.goto('/login');
  await page.getByLabel('Email').fill(USER_EMAIL);
  await page.getByLabel('Пароль').fill(USER_PASSWORD);
  await page.getByRole('button', { name: 'Войти' }).click();

  await page.goto(`/agents/${LLM_AGENT_SLUG}`);
  await page.getByRole('button', { name: 'Запустить агента' }).click();

  // Ожидаем toast с RU-сообщением про квоту
  await expect(
    page.getByText(/квота|лимит/i),
  ).toBeVisible({ timeout: 10_000 });
});
