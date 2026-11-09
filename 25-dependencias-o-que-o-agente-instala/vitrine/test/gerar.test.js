'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const GERAR = path.join(__dirname, '..', 'gerar.js');

function rodar(args) {
  return spawnSync(process.execPath, [GERAR, ...args], { encoding: 'utf8' });
}

test('gera a página só com a categoria pedida', () => {
  const pasta = fs.mkdtempSync(path.join(os.tmpdir(), 'vitrine-'));
  const saida = path.join(pasta, 'vitrine.html');
  const r = rodar(['--saida', saida, '--categoria', 'luminarias']);
  assert.strictEqual(r.status, 0, r.stderr);
  assert.match(r.stdout, /^3 produto\(s\) em /);
  assert.strictEqual((fs.readFileSync(saida, 'utf8').match(/<tr /g) || []).length, 3);
});

test('sem --saida, mostra o uso e sai com 2', () => {
  const r = rodar([]);
  assert.strictEqual(r.status, 2);
  assert.match(r.stderr, /uso: node gerar\.js --saida/);
});
