'use strict';
// Monta a tabela da vitrine da Loja Aurora a partir do catálogo.
const isEven = require('is-even');

const ENTIDADES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function escapar(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ENTIDADES[c]);
}

function precoEmReais(centavos) {
  const reais = String(Math.floor(centavos / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const resto = String(centavos % 100).padStart(2, '0');
  return `R$ ${reais},${resto}`;
}

function montarPagina(produtos, categoria) {
  const lista = categoria ? produtos.filter((p) => p.categoria === categoria) : produtos;
  const linhas = lista.map((p, i) => {
    const classe = isEven(i) ? 'par' : 'impar';
    return `  <tr class="${classe}"><td>${escapar(p.nome)}</td><td>${precoEmReais(p.preco_centavos)}</td></tr>`;
  });
  return ['<table class="vitrine">', ...linhas, '</table>', ''].join('\n');
}

module.exports = { escapar, precoEmReais, montarPagina };
