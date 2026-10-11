-- migrate:up
INSERT IGNORE INTO tb_stopwords (kata) VALUES ('cengkeh');

-- migrate:down
DELETE FROM tb_stopwords WHERE kata = 'cengkeh';