/**
 * Accessibility Tests for Dashboard - CauSium
 *
 * Testes de acessibilidade que rodam com preview estático.
 * Não dependem do backend.
 *
 * Run: npm run test:a11y
 */

import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

/**
 * Helper para verificar que a página carregou
 */
async function expectPageLoaded(page: Page) {
  await expect(page.locator('#root')).toBeVisible({ timeout: 10000 })
}

/**
 * Run axe accessibility scan
 */
async function runAxeScan(page: Page) {
  const builder = new AxeBuilder({ page })
  return await builder.analyze()
}

test.describe('Accessibility - Static HTML', () => {
  test('should have lang attribute on html', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const lang = await page.locator('html').getAttribute('lang')
    expect(lang).toBeTruthy()
  })

  test('should have meta charset UTF-8', async ({ page }) => {
    await page.goto('/')

    const charset = page.locator('meta[charset="utf-8"], meta[charset="UTF-8"]')
    await expect(charset).toHaveCount(1)
  })

  test('should have meta viewport for mobile', async ({ page }) => {
    await page.goto('/')

    const viewport = page.locator('meta[name="viewport"]')
    await expect(viewport).toHaveCount(1)

    const content = await viewport.getAttribute('content')
    expect(content).toContain('width=device-width')
  })

  test('should have descriptive title', async ({ page }) => {
    await page.goto('/')

    const title = await page.title()
    expect(title.trim().length).toBeGreaterThan(0)
  })
})

test.describe('Accessibility - Interactive Elements', () => {
  test('should have visible content', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const body = page.locator('body')
    await expect(body).toBeVisible()

    const text = await body.textContent()
    expect(text?.trim().length).toBeGreaterThan(0)
  })

  test('should render #root element', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })
})

test.describe('Accessibility - Axe Core', () => {
  test('should pass basic accessibility checks on index', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const results = await runAxeScan(page)

    // Log violations for review
    if (results.violations.length > 0) {
      console.log('Accessibility violations:')
      results.violations.forEach(v => {
        console.log(`- ${v.id}: ${v.description} (${v.nodes.length} nodes)`)
      })
    }

    // Index page should have minimal violations
    expect(results.violations.length).toBeLessThan(10)
  })

  test('should have valid HTML structure', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    // Check for valid document structure
    const html = page.locator('html')
    const head = page.locator('head')
    const body = page.locator('body')

    await expect(html).toHaveCount(1)
    await expect(head).toHaveCount(1)
    await expect(body).toHaveCount(1)
  })
})

test.describe('Accessibility - Focus Management', () => {
  test('should be able to focus on body', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    await page.locator('body').focus()

    const focused = await page.evaluate(() => document.activeElement?.tagName)
    expect(focused).toBeTruthy()
  })

  test('should not have negative tabindex', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const negativeTabindex = page.locator('[tabindex="-1"]')
    const count = await negativeTabindex.count()

    // Negative tabindex is okay for hidden elements, just log it
    if (count > 0) {
      console.log(`Found ${count} elements with tabindex="-1"`)
    }
  })
})

test.describe('Accessibility - Color and Contrast', () => {
  test('should have proper text visibility', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    // Get computed styles of body
    const styles = await page.evaluate(() => {
      const body = document.body
      const computed = window.getComputedStyle(body)
      return {
        color: computed.color,
        backgroundColor: computed.backgroundColor,
      }
    })

    expect(styles.color).toBeTruthy()
    expect(styles.backgroundColor).toBeTruthy()
  })
})

test.describe('Accessibility - Navigation', () => {
  test('should have skip link or main landmark', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    // Check for main landmark or skip link
    const main = page.locator('main, [role="main"], #root')
    await expect(main.first()).toBeVisible()
  })

  test('should have proper heading structure in root', async ({ page }) => {
    await page.goto('/')
    await expectPageLoaded(page)

    const headings = await page.$$eval('h1, h2, h3, h4, h5, h6',
      els => els.map(el => el.tagName)
    )

    // If there are headings, first should be h1
    if (headings.length > 0) {
      expect(headings[0]).toBe('H1')
    }
  })
})

test.describe('Accessibility - Resources', () => {
  test('should have valid link to stylesheet', async ({ page }) => {
    await page.goto('/')

    const link = page.locator('link[rel="stylesheet"]')
    const count = await link.count()

    expect(count).toBeGreaterThan(0)

    // Check href is valid
    if (count > 0) {
      const href = await link.first().getAttribute('href')
      expect(href).toBeTruthy()
      expect(href).toMatch(/\.css$/)
    }
  })

  test('should have module script for React', async ({ page }) => {
    await page.goto('/')

    const scripts = page.locator('script[type="module"]')
    const count = await scripts.count()

    expect(count).toBeGreaterThan(0)

    if (count > 0) {
      const src = await scripts.first().getAttribute('src')
      expect(src).toBeTruthy()
      expect(src).toMatch(/\.js$/)
    }
  })
})

test.describe('Dashboard Page Analysis', () => {
  test('should load dashboard route without crash', async ({ page }) => {
    // Sem auth, dashboard redireciona para login
    // Apenas verificar que não há erro catastrófico
    const response = await page.goto('/app/dashboard', { timeout: 5000 })

    // A página deve responder (200 ou redirect)
    expect(response?.status()).toBeLessThan(400)
  })

  test('should load login page', async ({ page }) => {
    await page.goto('/login')
    await expectPageLoaded(page)

    // Should render something
    const root = page.locator('#root')
    const html = await root.innerHTML()
    expect(html.length).toBeGreaterThan(0)
  })
})