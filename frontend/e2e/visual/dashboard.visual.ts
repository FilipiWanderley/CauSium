/**
 * Visual Tests for Dashboard - CauSium
 *
 * Testes simplificados que rodam com preview estático.
 * Não dependem do backend.
 *
 * Run: npm run test:visual
 */

import { test, expect, type Page } from '@playwright/test'

// Viewport sizes for responsive testing
const VIEWPORTS = {
  mobile: { width: 375, height: 667 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1280, height: 720 },
  wide: { width: 1440, height: 900 },
}

/**
 * Helper para verificar que a página carregou
 */
async function expectPageLoaded(page: Page) {
  await expect(page.locator('#root')).toBeVisible({ timeout: 10000 })
}

/**
 * Helper para verificar overflow horizontal
 */
async function expectNoHorizontalOverflow(page: Page) {
  const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
  const windowWidth = await page.evaluate(() => window.innerWidth)
  expect(bodyWidth).toBeLessThanOrEqual(windowWidth + 5)
}

test.describe('Dashboard Static Analysis', () => {
  test('should load index page', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    // Verificar título
    await expect(page).toHaveTitle(/CauSium/)
  })

  test('should have no console errors on load', async ({ page }) => {
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    await page.goto('/')
    await expectPageLoaded(page)
    await page.waitForTimeout(1000)

    // Filtrar erros conhecidos que não são críticos
    const criticalErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('404') &&
      !e.includes('Failed to load resource') &&
      !e.includes('unicornstudio') &&  // Script externo WebGL
      !e.includes('WebGL') &&           // Erros de WebGL de libs externas
      !e.includes('TextureLoader')
    )

    expect(criticalErrors).toHaveLength(0)
  })
})

test.describe('Dashboard Login Page', () => {
  test('should load login page', async ({ page }) => {
    await page.goto('/login')
    await expectPageLoaded(page)

    // Verificar elementos do login
    await expect(page.locator('body')).toBeVisible()
  })

  test('should have proper meta tags', async ({ page }) => {
    await page.goto('/')

    const viewport = await page.locator('meta[name="viewport"]')
    await expect(viewport).toHaveAttribute('content', /width=device-width/)
  })
})

test.describe('Static Assets', () => {
  test('should load CSS bundle', async ({ page }) => {
    const response = await page.goto('/')
    expect(response?.status()).toBe(200)

    // Verificar que CSS carregou
    const link = page.locator('link[rel="stylesheet"]')
    await expect(link).toHaveCount(1)
  })

  test('should load JS bundle', async ({ page }) => {
    await page.goto('/')

    const scripts = page.locator('script[type="module"]')
    const count = await scripts.count()
    expect(count).toBeGreaterThan(0)
  })

  test('should have favicon', async ({ page }) => {
    const response = await page.goto('/favicon.svg')
    expect(response?.status()).toBe(200)
  })
})

test.describe('Responsive Layout Analysis', () => {
  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`should fit at ${name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await page.goto('/')
      await expectPageLoaded(page)

      // Verificar overflow
      await expectNoHorizontalOverflow(page)

      // Screenshot
      await page.screenshot({
        path: `test-results/screenshots/index-${name}.png`
      })
    })
  }
})

test.describe('Component Rendering', () => {
  test('should render React root', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const root = page.locator('#root')
    const html = await root.innerHTML()

    // Verificar que React renderizou algo
    expect(html.length).toBeGreaterThan(100)
  })

  test('should not have broken images', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const images = page.locator('img')
    const count = await images.count()

    if (count > 0) {
      // Verificar que imagens têm src
      const firstImage = images.first()
      const src = await firstImage.getAttribute('src')
      expect(src).toBeTruthy()
    }
  })
})

test.describe('Accessibility - Static', () => {
  test('should have lang attribute', async ({ page }) => {
    await page.goto('/')

    const html = page.locator('html')
    const lang = await html.getAttribute('lang')
    expect(lang).toBeTruthy()
  })

  test('should have meta description', async ({ page }) => {
    await page.goto('/')

    const meta = page.locator('meta[name="description"]')
    // Não é obrigatório, mas é boa prática
    const exists = await meta.count() > 0
    if (exists) {
      const content = await meta.getAttribute('content')
      expect(content?.length).toBeGreaterThan(0)
    }
  })

  test('should have proper title', async ({ page }) => {
    await page.goto('/')

    const title = await page.title()
    expect(title).toBeTruthy()
    expect(title.length).toBeGreaterThan(5)
  })

  test('should have meta viewport', async ({ page }) => {
    await page.goto('/')

    const viewport = page.locator('meta[name="viewport"]')
    await expect(viewport).toHaveCount(1)

    const content = await viewport.getAttribute('content')
    expect(content).toContain('width=device-width')
  })
})

test.describe('Performance - Resource Loading', () => {
  test('should load within reasonable time', async ({ page }) => {
    const start = Date.now()
    await page.goto('/', { waitUntil: 'domcontentloaded' })
    const loadTime = Date.now() - start

    // Deve carregar em menos de 3 segundos
    expect(loadTime).toBeLessThan(3000)
  })
})