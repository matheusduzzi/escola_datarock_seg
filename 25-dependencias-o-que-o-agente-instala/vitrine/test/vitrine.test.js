'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { escapar, precoEmReais, montarPagina } = require('../vitrine');
const produtos = require('../catalogo.json');

test('preço em reais, com vírgula e ponto de milhar', () => {
  assert.strictEqual(precoEmReais(24990), 'R$ 249,90');
  assert.strictEqual(precoEmReais(6990), 'R$ 69,90');
  assert.strictEqual(precoEmReais(129900), 'R$ 1.299,00');
});

test('linhas alternam par e impar, começando por par', () => {
  const html = montarPagina(produtos, 'luminarias');
  const classes = [...html.matchAll(/<tr class="(\w+)">/g)].map((m) => m[1]);
  assert.deepStrictEqual(classes, ['par', 'impar', 'par']);
});

test('a categoria filtra os produtos', () => {
  assert.strictEqual((montarPagina(produtos, 'texteis').match(/<tr /g) || []).length, 2);
  assert.strictEqual((montarPagina(produtos).match(/<tr /g) || []).length, 7);
});

test('nome de produto vira texto, não HTML', () => {
  assert.strictEqual(escapar('Linho & Lã <b>'), 'Linho &amp; Lã &lt;b&gt;');
  assert.match(montarPagina(produtos, 'texteis'), /Linho &amp; Lã/);
});
