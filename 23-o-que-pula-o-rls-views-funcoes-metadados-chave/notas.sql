-- Porta 5. As notas fiscais em PDF ficam no bucket "notas", com o número do pedido no nome.
set client_min_messages = warning;
-- Rode com: python3 portas.py montar (ele roda o loja.sql e depois este).
-- Não apaga nada do storage: se você rodar de novo, ele volta o bucket e os donos ao começo.

insert into storage.buckets (id, name, public) values ('notas', 'notas', true)
  on conflict (id) do update set public = true;

insert into storage.objects (bucket_id, name, owner_id) values
  ('notas', 'nota-1001.pdf', 'b1a00000-0000-4000-8000-000000000001'),
  ('notas', 'nota-1002.pdf', 'b1a00000-0000-4000-8000-000000000001'),
  ('notas', 'nota-1003.pdf', 'ca100000-0000-4000-8000-000000000002'),
  ('notas', 'nota-1004.pdf', 'd0da0000-0000-4000-8000-000000000003')
  on conflict (bucket_id, name) do update set owner_id = excluded.owner_id;

drop policy if exists "notas: qualquer um lista" on storage.objects;
create policy "notas: qualquer um lista" on storage.objects
  for select to public using (bucket_id = 'notas');
