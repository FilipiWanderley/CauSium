/**
 * Bundle Analyzer Script - CauSium Frontend
 *
 * Analisa o bundle do frontend e gera relatório de tamanho.
 *
 * Run: npm run analyze:bundle
 */

import { existsSync, mkdirSync, writeFileSync, readdirSync, statSync } from 'fs'
import { join } from 'path'
import { spawn } from 'child_process'

const OUTPUT_DIR = 'test-results/bundle-analysis'
const REPORT_FILE = `${OUTPUT_DIR}/bundle-report.html`

/**
 * Target sizes (gzip in KB)
 */
const BUNDLE_TARGETS = {
  'main.js': 250,
  'index.css': 50,
  total: 300,
}

/**
 * Check if build output exists
 */
function checkBuildExists() {
  const distPath = 'dist/assets'

  if (!existsSync(distPath)) {
    console.error('❌ Build not found. Run "npm run build" first.')
    process.exit(1)
  }

  return distPath
}

/**
 * Get file sizes from dist/assets (pure ESM)
 */
function getFileSizes() {
  const dir = 'dist/assets'
  if (!existsSync(dir)) return []

  return readdirSync(dir)
    .filter(f => f.endsWith('.js') || f.endsWith('.css'))
    .map(name => ({
      Name: name,
      Length: statSync(join(dir, name)).size
    }))
}

/**
 * Generate bundle report
 */
function generateReport(files, totalGzip, totalJS, totalCSS) {
  const detailedFiles = files.map(file => {
    const sizeKB = file.Length / 1024
    const sizeGzip = estimateGzipSize(sizeKB)

    return {
      name: file.Name,
      size: sizeKB,
      sizeGzip,
      status: sizeGzip > BUNDLE_TARGETS.total ? '🔴' :
              sizeGzip > BUNDLE_TARGETS.total * 0.8 ? '🟡' : '🟢'
    }
  })

  // Generate HTML report
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bundle Analysis - CauSium</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 2rem; background: #0f172a; color: #e2e8f0; }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { font-size: 1.5rem; margin-bottom: 1rem; color: #f8fafc; }
    h2 { font-size: 1.1rem; margin: 1.5rem 0 0.75rem; color: #94a3b8; }
    .card { background: #1e293b; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
    .stat { background: #334155; border-radius: 6px; padding: 1rem; }
    .stat-value { font-size: 1.5rem; font-weight: 600; }
    .stat-label { font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem; }
    .stat-ok { color: #22c55e; }
    .stat-warn { color: #eab308; }
    .stat-fail { color: #ef4444; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #334155; }
    th { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; }
    tr:hover { background: #334155; }
    .pass { color: #22c55e; }
    .fail { color: #ef4444; }
    code { background: #334155; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem; }
    .target { font-size: 0.75rem; color: #64748b; margin-top: 0.5rem; }
    .badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; }
    .badge-large { font-size: 3rem; margin-bottom: 0.5rem; }
    .badge-green { background: #22c55e; color: #fff; }
    .badge-yellow { background: #eab308; color: #000; }
    .badge-red { background: #ef4444; color: #fff; }
  </style>
</head>
<body>
  <div class="container">
    <h1>📦 CauSium Bundle Analysis</h1>
    <p style="color: #94a3b8; margin-bottom: 1rem;">Generated: ${new Date().toISOString()}</p>

    <div class="card">
      <h2>Summary</h2>
      <div class="grid">
        <div class="stat">
          <div class="stat-value ${totalGzip < BUNDLE_TARGETS.total ? 'stat-ok' : 'stat-fail'}">${totalGzip.toFixed(1)} KB</div>
          <div class="stat-label">Total (gzip)</div>
        </div>
        <div class="stat">
          <div class="stat-value">${estimateGzipSize(totalJS).toFixed(1)} KB</div>
          <div class="stat-label">JavaScript (gzip)</div>
        </div>
        <div class="stat">
          <div class="stat-value">${estimateGzipSize(totalCSS).toFixed(1)} KB</div>
          <div class="stat-label">CSS (gzip)</div>
        </div>
        <div class="stat">
          <div class="stat-value">${files.length}</div>
          <div class="stat-label">Files</div>
        </div>
      </div>
      <p class="target">Target: < ${BUNDLE_TARGETS.total} KB gzip total</p>
    </div>

    <div class="card">
      <h2>Bundle Health</h2>
      <div style="text-align: center; margin: 1rem 0;">
        <div class="badge badge-large ${totalGzip < BUNDLE_TARGETS.total ? 'badge-green' : 'badge-red'}">
          ${totalGzip < BUNDLE_TARGETS.total ? '✅' : '❌'}
        </div>
        <p style="font-size: 1.25rem; font-weight: 600;">
          ${totalGzip < BUNDLE_TARGETS.total
            ? 'Bundle size is within target'
            : 'Bundle exceeds target'
          }
        </p>
        <p style="color: #94a3b8; margin-top: 0.5rem;">
          ${totalGzip < BUNDLE_TARGETS.total
            ? `${(BUNDLE_TARGETS.total - totalGzip).toFixed(1)} KB buffer available`
            : `${(totalGzip - BUNDLE_TARGETS.total).toFixed(1)} KB over target`
          }
        </p>
      </div>
    </div>

    <div class="card">
      <h2>File Breakdown</h2>
      <table>
        <thead>
          <tr>
            <th>File</th>
            <th>Raw</th>
            <th>Gzip (est.)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${detailedFiles.map(f => `
            <tr>
              <td><code>${f.name}</code></td>
              <td>${f.size.toFixed(1)} KB</td>
              <td>${f.sizeGzip.toFixed(1)} KB</td>
              <td>${f.status}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Recommendations</h2>
      <ul style="color: #94a3b8; font-size: 0.875rem; list-style: disc; padding-left: 1.5rem;">
        <li>Consider code-splitting large components (Recharts ~104KB gzip)</li>
        <li>Lazy load routes that are not immediately needed</li>
        <li>Analyze if all Lucide icons are being used</li>
        <li>Consider tree-shaking for date-fns</li>
        <li>Enable gzip/brotli compression on server</li>
      </ul>
    </div>
  </div>
</body>
</html>`

  return html
}

/**
 * Estimate gzip size (rough approximation: gzip ~35% of raw)
 */
function estimateGzipSize(sizeKB) {
  return sizeKB * 0.35
}

/**
 * Main execution
 */
async function main() {
  console.log('🔍 Analyzing bundle...\n')

  // Check if build exists
  checkBuildExists()

  // Get file sizes
  const files = getFileSizes()

  if (files.length === 0) {
    console.error('❌ No bundle files found')
    process.exit(1)
  }

  // Ensure output directory exists
  if (!existsSync(OUTPUT_DIR)) {
    mkdirSync(OUTPUT_DIR, { recursive: true })
  }

  // Calculate totals
  let totalJS = 0
  let totalCSS = 0

  console.log('📁 Files:')
  for (const file of files) {
    const sizeKB = file.Length / 1024
    const sizeGzip = estimateGzipSize(sizeKB)

    if (file.Name.endsWith('.js')) totalJS += sizeKB
    if (file.Name.endsWith('.css')) totalCSS += sizeKB

    const status = sizeGzip > BUNDLE_TARGETS.total ? '🔴' :
                   sizeGzip > BUNDLE_TARGETS.total * 0.8 ? '🟡' : '🟢'

    console.log(`  ${status} ${file.Name}: ${sizeKB.toFixed(1)} KB (${sizeGzip.toFixed(1)} KB gzip)`)
  }

  const totalGzip = estimateGzipSize(totalJS) + estimateGzipSize(totalCSS)

  console.log('\n📊 Summary:')
  console.log(`  JavaScript: ${estimateGzipSize(totalJS).toFixed(1)} KB gzip`)
  console.log(`  CSS: ${estimateGzipSize(totalCSS).toFixed(1)} KB gzip`)
  console.log(`  Total: ${totalGzip.toFixed(1)} KB gzip`)
  console.log(`  Target: < ${BUNDLE_TARGETS.total} KB gzip`)

  if (totalGzip < BUNDLE_TARGETS.total) {
    console.log(`\n✅ Bundle size is within target (${(BUNDLE_TARGETS.total - totalGzip).toFixed(1)} KB buffer)`)
  } else {
    console.log(`\n❌ Bundle exceeds target by ${(totalGzip - BUNDLE_TARGETS.total).toFixed(1)} KB`)
  }

  // Generate and save report
  const report = generateReport(files, totalGzip, totalJS, totalCSS)
  writeFileSync(REPORT_FILE, report)
  console.log(`\n📄 Report saved to: ${REPORT_FILE}`)

  // Open report
  try {
    spawn('cmd', ['/c', 'start', REPORT_FILE], { detached: true, stdio: 'ignore' })
  } catch (e) {
    // Ignore if can't open browser
  }
}

main().catch(console.error)