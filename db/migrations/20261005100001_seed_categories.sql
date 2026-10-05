-- migrate:up
INSERT INTO tb_kategori (nama) VALUES
('Cara Tanam'),
('Perawatan'),
('Nutrisi & Kesuburan'),
('Hama'),
('Penyakit'),
('Diagnosa Tanaman'),
('Bunga & Pembentukan Bunga'),
('Panen'),
('Cuaca & Lingkungan'),
('Pascapanen');

-- migrate:down
DELETE FROM tb_kategori;