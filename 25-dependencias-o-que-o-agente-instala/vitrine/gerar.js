'use strict';
// Gera a página da vitrine: node gerar.js --saida vitrine.html [--categoria luminarias]
const fs = require('fs');
const path = require('path');
const parse = require('minimist');
const { montarPagina } = require('./vitrine');

function main(argv) {
  const opcoes = parse(argv, {
    string: ['saida', 'categoria', 'catalogo'],
    default: { catalogo: path.join(__dirname, 'catalogo.json') },
  });
  if (!opcoes.saida) {
    console.error('uso: node gerar.js --saida ARQUIVO [--categoria NOME]');
    return 2;
  }
  const produtos = JSON.parse(fs.readFileSync(opcoes.catalogo, 'utf8'));
  const html = montarPagina(produtos, opcoes.categoria);
  fs.writeFileSync(opcoes.saida, html);
  const n = (html.match(/<tr /g) || []).length;
  console.log(`${n} produto(s) em ${opcoes.saida}`);
  return 0;
}

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}

module.exports = { main };
