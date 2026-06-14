#!/usr/bin/env node
// memory-eviction.js — Score-based memory eviction for OpenClaw
//
// Scans memory/projects/*.md, scores each entry, archives low-scoring ones.
// P0 entries are never touched. MEMORY.md is not modified (use sync-skeleton.py).
//
// Usage:
//   node memory-eviction.js [--dry-run] [--threshold N] [--workspace PATH]

const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');

// ─── Config ───
const ARGS = process.argv.slice(2);
const DRY_RUN = ARGS.includes('--dry-run');
const THRESHOLD = parseFloat(ARGS.find((_, i, a) => a[i - 1] === '--threshold') || '2.0');
const WORKSPACE = ARGS.find((_, i, a) => a[i - 1] === '--workspace')
  || path.join(os.homedir(), '.openclaw', 'workspace');

const PROJECTS_DIR = path.join(WORKSPACE, 'memory', 'projects');
const ARCHIVE_DIR = path.join(WORKSPACE, 'memory', 'archive');
const HIT_DB = path.join(WORKSPACE, 'memory', '.hit-tracker.db');

// ─── Parser ───
// CRITICAL: match only bullet-point starts to avoid false positives in prose
const ENTRY_RE = /^\s*-\s*\[(P[012])\]\[(\d{4}-\d{2}-\d{2})\](?:\[src:(\w+)\])?\s*(.+)$/;

function parseLine(line) {
  const m = line.match(ENTRY_RE);
  if (!m) return null;
  return {
    raw: line,
    priority: m[1],
    createdAt: new Date(m[2]),
    source: m[3] || 'unknown',
    content: m[4],
  };
}

// ─── Scoring ───
const W = { P0: 1000, P1: 10, P2: 1 };
const HALF_LIFE = { P0: Infinity, P1: 90, P2: 30 };
const SRC_BONUS = { user: 1.3, infer: 1.0, system: 0.9, unknown: 1.0 };

function score(entry, hitData, now) {
  const daysSinceCreated = (now - entry.createdAt) / 86400000;
  const hl = HALF_LIFE[entry.priority];
  const decay = hl === Infinity ? 1.0 : Math.pow(0.5, daysSinceCreated / hl);

  // Hit data: look up by content prefix (first 60 chars)
  const key = entry.content.slice(0, 60).trim();
  const hit = hitData.get(key) || { count: 0, lastHit: null };

  let heat;
  if (hit.count === 0) {
    heat = 0.5;
  } else {
    const daysSinceHit = hit.lastHit
      ? (now - new Date(hit.lastHit)) / 86400000
      : Infinity;
    const recency = Math.max(0.1, 1.0 - daysSinceHit / 30);
    const frequency = Math.min(3.0, 1.0 + Math.log2(hit.count));
    heat = recency * frequency;
  }

  const srcBonus = SRC_BONUS[entry.source] || 1.0;
  return W[entry.priority] * decay * heat * srcBonus;
}

// ─── Hit Data (optional, from SQLite) ───
function loadHitData() {
  const data = new Map();
  // If hit-tracker DB exists and we have better-sqlite3, load it.
  // Otherwise return empty map — scoring still works, just without hit boost.
  try {
    if (!fs.existsSync(HIT_DB)) return data;
    // Attempt native sqlite3 (Node 22+)
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(HIT_DB, { open: true });
    const rows = db.prepare('SELECT file_path, line_start, hit_count, last_hit FROM hits').all();
    for (const row of rows) {
      data.set(`${row.file_path}:${row.line_start}`, {
        count: row.hit_count,
        lastHit: row.last_hit,
      });
    }
    db.close();
  } catch {
    // No sqlite available — proceed without hit data
  }
  return data;
}

// ─── Dedup Archive ───
function loadExistingArchive(archiveFile) {
  if (!fs.existsSync(archiveFile)) return new Set();
  const content = fs.readFileSync(archiveFile, 'utf-8');
  const hashes = new Set();
  for (const line of content.split('\n')) {
    if (parseLine(line)) {
      hashes.add(crypto.createHash('md5').update(line.trim()).digest('hex'));
    }
  }
  return hashes;
}

// ─── Atomic Write ───
function atomicWrite(filepath, content) {
  const tmp = filepath + '.tmp.' + process.pid;
  fs.writeFileSync(tmp, content, 'utf-8');
  fs.renameSync(tmp, filepath);
}

// ─── Main ───
function run() {
  const now = new Date();
  const hitData = loadHitData();

  if (!fs.existsSync(PROJECTS_DIR)) {
    console.log('No memory/projects/ directory. Nothing to evict.');
    return;
  }

  const files = fs.readdirSync(PROJECTS_DIR).filter(f => f.endsWith('.md'));
  let totalEvicted = 0;
  let totalKept = 0;

  for (const file of files) {
    const filepath = path.join(PROJECTS_DIR, file);
    const lines = fs.readFileSync(filepath, 'utf-8').split('\n');

    const keep = [];
    const evict = [];

    for (const line of lines) {
      const entry = parseLine(line);
      if (!entry) { keep.push(line); continue; }
      if (entry.priority === 'P0') { keep.push(line); continue; }

      const s = score(entry, hitData, now);
      if (s < THRESHOLD) {
        evict.push({ ...entry, score: s });
      } else {
        keep.push(line);
      }
    }

    if (evict.length === 0) {
      totalKept += keep.filter(l => parseLine(l)).length;
      continue;
    }

    const keptEntries = keep.filter(l => parseLine(l)).length;
    totalKept += keptEntries;
    totalEvicted += evict.length;

    console.log(`\n📁 ${file}`);
    console.log(`   Keep: ${keptEntries} | Evict: ${evict.length}`);
    evict.sort((a, b) => a.score - b.score).forEach(e => {
      console.log(`   🗑️  [${e.priority}][src:${e.source}] s=${e.score.toFixed(2)} | ${e.content.slice(0, 55)}`);
    });

    if (!DRY_RUN) {
      // Write back project file
      atomicWrite(filepath, keep.join('\n'));

      // Append to monthly archive (with dedup)
      if (!fs.existsSync(ARCHIVE_DIR)) fs.mkdirSync(ARCHIVE_DIR, { recursive: true });
      const archiveFile = path.join(ARCHIVE_DIR, `${now.toISOString().slice(0, 7)}.md`);
      const existingHashes = loadExistingArchive(archiveFile);

      const newArchiveLines = [];
      for (const e of evict) {
        const hash = crypto.createHash('md5').update(e.raw.trim()).digest('hex');
        if (!existingHashes.has(hash)) {
          newArchiveLines.push(e.raw);
          existingHashes.add(hash);
        }
      }

      if (newArchiveLines.length > 0) {
        const header = `\n<!-- Archived: ${now.toISOString().slice(0, 10)} | Source: ${file} | Reason: score < ${THRESHOLD} -->\n`;
        fs.appendFileSync(archiveFile, header + newArchiveLines.join('\n') + '\n', 'utf-8');
      }
    }
  }

  // ─── MEMORY.md overflow warning ───
  const memoryFile = path.join(WORKSPACE, 'MEMORY.md');
  if (fs.existsSync(memoryFile)) {
    const memLines = fs.readFileSync(memoryFile, 'utf-8').split('\n')
      .filter(l => l.trim() && !l.trim().startsWith('<!--') && !l.trim().startsWith('#'));
    if (memLines.length > 50) {
      console.log(`\n⚠️  WARNING: MEMORY.md has ${memLines.length} content lines (limit: 50)`);
      console.log('   Run memory maintenance to triage overflow.');
    }
  }

  console.log(`\n${DRY_RUN ? '⚠️  DRY RUN |' : '✅'} Kept: ${totalKept} | Evicted: ${totalEvicted}`);
}

run();
