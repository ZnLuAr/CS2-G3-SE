import { expect, test } from '@playwright/test'

test('登录页提供账号密码输入和可访问名称', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: '登录账号' })).toBeVisible()
  await expect(page.getByLabel('账号', { exact: true })).toHaveAttribute('autocomplete', 'username')
  await expect(page.getByLabel('密码', { exact: true })).toHaveAttribute('type', 'password')
})

test('404页面能返回登录入口', async ({ page }) => {
  await page.goto('/missing-page')
  await expect(page.getByRole('heading', { name: '页面不存在' })).toBeVisible()
  await page.getByRole('link', { name: '返回首页' }).click()
  await expect(page).toHaveURL('/login')
})

test('mock：认证、刷新复核、越权导航和退出清理', async ({ page }) => {
  const actor = { accountId: '9007199254740993', role: 'member', memberId: '9223372036854775807', coachId: null }
  let verified = false
  await page.route('**/api/auth/login', async route => {
    const body = route.request().postDataJSON()
    expect(body).toEqual({ username: 'member_7', password: 'Pass_123' })
    await route.fulfill({ json: { accessToken: 'mock-token', tokenType: 'bearer', expiresAt: '2099-01-01T00:00:00Z', actor } })
  })
  await page.route('**/api/auth/me', async route => {
    expect(route.request().headers().authorization).toBe('Bearer mock-token')
    verified = true
    await route.fulfill({ json: actor })
  })
  await page.route('**/api/auth/logout', route => route.fulfill({ json: { loggedOut: true } }))
  await page.goto('/login')
  await page.getByLabel('账号', { exact: true }).fill('Member_7')
  await page.getByLabel('密码', { exact: true }).fill('Pass_123')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).toHaveURL('/sessions')
  await expect(page.getByRole('heading', { name: '课程安排' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '功能准备中' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: '课程安排' })).toBeVisible()
  expect(verified).toBe(true)
  await expect(page.getByText('会员 · 账号 9007199254740993', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: '我的资料', exact: true }).click()
  await expect(page).toHaveURL('/profile')
  await expect(page.getByRole('heading', { name: '我的资料' })).toBeVisible()
  await page.getByRole('link', { name: '我的订单', exact: true }).click()
  await expect(page).toHaveURL('/orders')
  await expect(page.getByRole('heading', { name: '我的订单' })).toBeVisible()
  await page.goto('/admin/accounts')
  await expect(page.getByRole('heading', { name: '无权访问' })).toBeVisible()
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page).toHaveURL('/login')
  expect(await page.evaluate(() => sessionStorage.getItem('gym.session'))).toBeNull()
})

test('mock：401身份失效清除凭据并返回登录页', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('gym.session', JSON.stringify({ accessToken: 'expired-token', expiresAt: '2099-01-01T00:00:00Z' }))
  })
  await page.route('**/api/auth/me', route => route.fulfill({
    status: 401,
    json: { message: '登录已失效', action: 'login', errorType: 'AuthenticationError', requestId: null, recordId: null },
  }))
  await page.goto('/sessions')
  await expect(page).toHaveURL('/login')
  expect(await page.evaluate(() => sessionStorage.getItem('gym.session'))).toBeNull()
})

test('mock：退出返回exit时清理身份并保留服务不可用反馈', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('gym.session', JSON.stringify({ accessToken: 'mock-token', expiresAt: '2099-01-01T00:00:00Z' }))
  })
  await page.route('**/api/auth/me', route => route.fulfill({
    json: { accountId: '7', role: 'member', memberId: '12', coachId: null },
  }))
  await page.route('**/api/auth/logout', route => route.fulfill({
    status: 503,
    json: { message: '服务正在恢复，请稍后重试。', action: 'exit', errorType: 'StorageError', requestId: null, recordId: null },
  }))
  await page.goto('/sessions')
  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page).toHaveURL('/service-unavailable')
  await expect(page.getByRole('heading', { name: '服务暂时不可用' })).toBeVisible()
  await expect(page.getByText('服务正在恢复，请稍后重试。')).toBeVisible()
  expect(await page.evaluate(() => sessionStorage.getItem('gym.session'))).toBeNull()
})
