-- migrate:up

CREATE TABLE IF NOT EXISTS tb_stopwords (
  id   INT PRIMARY KEY AUTO_INCREMENT,
  kata VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

INSERT IGNORE INTO tb_stopwords (kata)  VALUES
  -- Pronouns & demonstratives
  ('aku'), ('saya'), ('kamu'), ('anda'), ('dia'), ('ia'),
  ('kami'), ('kita'), ('mereka'),
  ('ini'), ('itu'), ('sini'), ('sana'), ('situ'),
  ('siapa'), ('apa'), ('mana'), ('yang'), ('yg'),

  -- Question words
  ('apakah'), ('bagaimana'), ('bagaimanakah'), ('kenapa'), ('mengapa'),
  ('kapan'), ('bilamana'), ('dimana'), ('kemana'), ('berapa'),
  ('adakah'), ('bisakah'), ('bolehkah'),

  -- Prepositions
  ('di'), ('ke'), ('dari'), ('pada'), ('dalam'), ('dengan'),
  ('untuk'), ('oleh'), ('tentang'), ('kepada'), ('terhadap'),
  ('seperti'), ('bagi'), ('akan'),
  ('sampai'), ('hingga'), ('sejak'), ('antara'), ('melalui'),

  -- Conjunctions & connectors
  ('dan'), ('atau'), ('tapi'), ('tetapi'), ('namun'), ('melainkan'),
  ('karena'), ('sebab'), ('jika'), ('kalau'), ('bila'), ('apabila'),
  ('agar'), ('supaya'), ('sehingga'), ('maka'),
  ('bahwa'), ('serta'), ('juga'), ('pula'), ('bahkan'),

  -- Articles & particles
  ('si'), ('sang'), ('para'), ('kaum'),
  ('lah'), ('kah'), ('pun'), ('nya'),
  ('adalah'), ('ialah'), ('merupakan'),
  ('ya'),  ('bukan'),  ('sudah'), ('telah'),
  ('masih'),  ('pernah'),

  -- Intensifiers & fillers
  ('sangat'), ('amat'), ('sekali'), ('agak'), 
  ('lebih'), ('paling'), ('hanya'), ('saja'), ('sahaja'),
  ('sering'), ('jarang'), ('selalu'), ('kadang'),
  ('mungkin'), ('barangkali'), ('tentu'), ('pasti'),

  -- Generic verbs
  ('ada'), ('jadi'), ('menjadi'),
  ('buat'), ('membuat'), ('dibuat'),
  ('dapat'), ('bisa'), ('mampu'),
  ('harus'), ('wajib'), ('perlu'), ('butuh'),
  ('ingin'), ('mau'), ('hendak'),
  ('minta'), ('meminta'),
  ('beri'), ('memberi'),
  ('ambil'), ('mengambil'),
  ('lihat'), ('melihat'),
  ('tahu'), ('mengetahui'),
  ('coba'), ('mencoba'),
  ('pakai'), ('memakai'), ('gunakan'), ('menggunakan'),
  ('bantu'), ('membantu'),

  -- Time words
  ('hari'),  ('ketika'), 
  ('sekarang'), ('tadi'), ('nanti'), ('besok'), ('kemarin'),
  ('selama'), ('sebelum'), ('sesudah'), 
  ('terus'), ('lalu'), ('kemudian');

-- migrate:down
DROP TABLE IF EXISTS tb_stopwords;