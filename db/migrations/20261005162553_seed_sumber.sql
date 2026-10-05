-- migrate:up
INSERT INTO tb_sumber (kode, judul) VALUES
  ('S1', 'Kementan — Buku Saku Pengenalan dan Pengendalian OPT pada Tanaman Cengkeh (2021)'),
  ('S2', 'Kementan — Teknik Persemaian Tanaman Cengkeh'),
  ('S3', 'Balittro/Kementan — Petunjuk Teknis Pembenihan/Perbenihan Tanaman Cengkeh'),
  ('S4', 'Ditjenbun/Kementan — BPKC/Pseudomonas syzygii'),
  ('S5', 'Kementan — pedoman teknis budidaya, lingkungan, pembungaan, panen dan pascapanen'),
  ('S6', 'Kementan/Ditjenbun — monitoring, sanitasi dan pengelolaan OPT');

-- migrate:down
DELETE FROM tb_sumber WHERE kode IN ('S1', 'S2', 'S3', 'S4', 'S5', 'S6');