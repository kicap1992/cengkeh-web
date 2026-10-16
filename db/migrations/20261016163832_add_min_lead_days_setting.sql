-- migrate:up
INSERT INTO tb_setting (kunci, nilai, deskripsi) VALUES
  ('min_lead_days', '1', 'Jumlah hari minimum sebelum tanggal mulai. Booking untuk hari ini tidak diizinkan jika nilainya 1.');

-- migrate:down
DELETE FROM tb_setting WHERE kunci = 'min_lead_days';