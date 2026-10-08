-- migrate:up

-- tb_variasi: one variation text per question
ALTER TABLE tb_variasi
  ADD UNIQUE KEY uq_variasi_pertanyaan_teks (pertanyaan_id, teks(255));

-- tb_keyword: one keyword per question
ALTER TABLE tb_keyword
  ADD UNIQUE KEY uq_keyword_pertanyaan_kata (pertanyaan_id, kata);

-- tb_relasi: one relation pair (already PK'd, but explicit for clarity)
-- (No change needed — tb_relasi already uses PRIMARY KEY (pertanyaan_id, related_id))

-- tb_pertanyaan_sumber: one source per question
-- (No change needed — tb_pertanyaan_sumber already uses PRIMARY KEY (pertanyaan_id, sumber_id))

-- tb_follow_up: one follow-up with the same question per parent QA
ALTER TABLE tb_follow_up
  ADD UNIQUE KEY uq_follow_up_pertanyaan_urutan (pertanyaan_id, urutan);

-- tb_follow_option: one option with the same label per follow-up
ALTER TABLE tb_follow_option
  ADD UNIQUE KEY uq_follow_option_follow_label (follow_up_id, label);

-- tb_option_next_qa: one next_qa per option
-- (No change needed — already PK'd as (option_id, next_qa_id))

-- migrate:down

ALTER TABLE tb_follow_option
  DROP KEY uq_follow_option_follow_label;

ALTER TABLE tb_follow_up
  DROP KEY uq_follow_up_pertanyaan_urutan;

ALTER TABLE tb_keyword
  DROP KEY uq_keyword_pertanyaan_kata;

ALTER TABLE tb_variasi
  DROP KEY uq_variasi_pertanyaan_teks;