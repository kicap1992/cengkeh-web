-- migrate:up
CREATE TABLE tb_kategori (
  id INT PRIMARY KEY AUTO_INCREMENT,
  nama VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE tb_sumber (
  id INT PRIMARY KEY AUTO_INCREMENT,
  kode VARCHAR(10) NOT NULL UNIQUE,
  judul TEXT NOT NULL
) ENGINE=InnoDB;

CREATE TABLE tb_pertanyaan (
  id INT PRIMARY KEY,
  kategori_id INT NOT NULL,
  tipe ENUM('informational','diagnostic','solution') NOT NULL,
  pertanyaan TEXT NOT NULL,
  jawaban TEXT,
  FOREIGN KEY (kategori_id) REFERENCES tb_kategori(id)
) ENGINE=InnoDB;

CREATE TABLE tb_variasi (
  id INT PRIMARY KEY AUTO_INCREMENT,
  pertanyaan_id INT NOT NULL,
  teks TEXT NOT NULL,
  FOREIGN KEY (pertanyaan_id) REFERENCES tb_pertanyaan(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE tb_keyword (
  id INT PRIMARY KEY AUTO_INCREMENT,
  pertanyaan_id INT NOT NULL,
  kata VARCHAR(100) NOT NULL,
  FOREIGN KEY (pertanyaan_id) REFERENCES tb_pertanyaan(id) ON DELETE CASCADE,
  INDEX idx_kata (kata)
) ENGINE=InnoDB;

CREATE TABLE tb_relasi (
  pertanyaan_id INT NOT NULL,
  related_id INT NOT NULL,
  PRIMARY KEY (pertanyaan_id, related_id),
  FOREIGN KEY (pertanyaan_id) REFERENCES tb_pertanyaan(id) ON DELETE CASCADE,
  FOREIGN KEY (related_id)   REFERENCES tb_pertanyaan(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE tb_pertanyaan_sumber (
  pertanyaan_id INT NOT NULL,
  sumber_id INT NOT NULL,
  PRIMARY KEY (pertanyaan_id, sumber_id),
  FOREIGN KEY (pertanyaan_id) REFERENCES tb_pertanyaan(id) ON DELETE CASCADE,
  FOREIGN KEY (sumber_id)    REFERENCES tb_sumber(id)
) ENGINE=InnoDB;

CREATE TABLE tb_follow_up (
  id INT PRIMARY KEY AUTO_INCREMENT,
  pertanyaan_id INT NOT NULL,
  urutan INT NOT NULL,
  pertanyaan TEXT NOT NULL,
  FOREIGN KEY (pertanyaan_id) REFERENCES tb_pertanyaan(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE tb_follow_option (
  id INT PRIMARY KEY AUTO_INCREMENT,
  follow_up_id INT NOT NULL,
  label VARCHAR(100) NOT NULL,
  value VARCHAR(50) NOT NULL,
  FOREIGN KEY (follow_up_id) REFERENCES tb_follow_up(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE tb_option_next_qa (
  option_id INT NOT NULL,
  next_qa_id INT NOT NULL,
  PRIMARY KEY (option_id, next_qa_id),
  FOREIGN KEY (option_id)   REFERENCES tb_follow_option(id) ON DELETE CASCADE,
  FOREIGN KEY (next_qa_id)  REFERENCES tb_pertanyaan(id)
) ENGINE=InnoDB;

-- migrate:down
DROP TABLE IF EXISTS tb_option_next_qa;
DROP TABLE IF EXISTS tb_follow_option;
DROP TABLE IF EXISTS tb_follow_up;
DROP TABLE IF EXISTS tb_pertanyaan_sumber;
DROP TABLE IF EXISTS tb_relasi;
DROP TABLE IF EXISTS tb_keyword;
DROP TABLE IF EXISTS tb_variasi;
DROP TABLE IF EXISTS tb_pertanyaan;
DROP TABLE IF EXISTS tb_sumber;
DROP TABLE IF EXISTS tb_kategori;