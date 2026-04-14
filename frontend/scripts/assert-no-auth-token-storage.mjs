#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'

const PROJECT_ROOT = process.cwd()
const SRC_DIR = path.join(PROJECT_ROOT, 'src')
const DIST_DIR = path.join(PROJECT_ROOT, 'dist')

const FILE_EXTENSIONS = new Set(['.ts', '.tsx', '.js', '.jsx'])
const SOURCE_IGNORED_SUFFIXES = ['.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx']

const STORAGE_USAGE_RE = /(?:localStorage|sessionStorage)\s*\.(?:setItem|getItem|removeItem)\s*\(\s*(['"`])([^'"`]+)\1/gi
const AUTH_KEY_RE = /(access|refresh|auth|jwt|bearer)[-_ ]?token/i

const BUNDLE_AUTH_STORAGE_RE = /(?:localStorage|sessionStorage).{0,160}(?:access|refresh|auth|jwt|bearer)[-_ ]?token|(?:access|refresh|auth|jwt|bearer)[-_ ]?token.{0,160}(?:localStorage|sessionStorage)/gis

function walkFiles(dir, collector) {
  if (!fs.existsSync(dir)) {
    return
  }

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walkFiles(fullPath, collector)
      continue
    }
    collector.push(fullPath)
  }
}

function isSourceFile(filePath) {
  const ext = path.extname(filePath)
  if (!FILE_EXTENSIONS.has(ext)) {
    return false
  }
  return !SOURCE_IGNORED_SUFFIXES.some((suffix) => filePath.endsWith(suffix))
}

function lineForIndex(text, index) {
  return text.slice(0, index).split('\n').length
}

function checkSourceFiles() {
  const files = []
  walkFiles(SRC_DIR, files)

  const violations = []

  for (const filePath of files) {
    if (!isSourceFile(filePath)) {
      continue
    }

    const text = fs.readFileSync(filePath, 'utf8')
    STORAGE_USAGE_RE.lastIndex = 0

    let match
    while ((match = STORAGE_USAGE_RE.exec(text)) !== null) {
      const storageKey = match[2]
      if (!AUTH_KEY_RE.test(storageKey)) {
        continue
      }
      violations.push({
        file: path.relative(PROJECT_ROOT, filePath),
        line: lineForIndex(text, match.index),
        snippet: match[0],
      })
    }
  }

  return violations
}

function checkBundleFiles() {
  const files = []
  walkFiles(DIST_DIR, files)

  const jsFiles = files.filter((filePath) => filePath.endsWith('.js'))
  if (jsFiles.length === 0) {
    return [{ file: 'dist', line: 1, snippet: 'No JS bundle files found. Run `npm run build` first.' }]
  }

  const violations = []
  for (const filePath of jsFiles) {
    const text = fs.readFileSync(filePath, 'utf8')
    BUNDLE_AUTH_STORAGE_RE.lastIndex = 0
    let match
    while ((match = BUNDLE_AUTH_STORAGE_RE.exec(text)) !== null) {
      violations.push({
        file: path.relative(PROJECT_ROOT, filePath),
        line: lineForIndex(text, match.index),
        snippet: match[0].slice(0, 180),
      })
    }
  }

  return violations
}

function main() {
  const sourceViolations = checkSourceFiles()
  const bundleViolations = checkBundleFiles()
  const allViolations = [...sourceViolations, ...bundleViolations]

  if (allViolations.length === 0) {
    console.log('OK: no auth token persistence in localStorage/sessionStorage (source + bundle).')
    process.exit(0)
  }

  console.error('FAIL: found auth token persistence patterns in storage.')
  for (const violation of allViolations) {
    console.error(`- ${violation.file}:${violation.line} :: ${violation.snippet}`)
  }
  process.exit(1)
}

main()