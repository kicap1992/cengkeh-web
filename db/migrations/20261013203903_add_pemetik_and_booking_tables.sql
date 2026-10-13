-- migrate:up

-- =========================================================================
-- tb_setting — generic key-value config table
-- =========================================================================
-- Use this for any runtime-configurable value the admin can change
-- without a code deploy: price_per_day, booking_expiry_hours, etc.
-- =========================================================================
CREATE TABLE tb_setting (
  kunci        VARCHAR(50)   PRIMARY KEY,
  nilai        VARCHAR(255)  NOT NULL,
  deskripsi    VARCHAR(255)  NULL,
  updated_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO tb_setting (kunci, nilai, deskripsi) VALUES
  ('price_per_day',        '100000',  'Harga sewa pemetik per hari (Rp)'),
  ('booking_expiry_hours', '24',      'Batas waktu pembayaran sebelum booking kedaluwarsa'),
  ('min_booking_days',     '1',       'Minimum hari pemesanan'),
  ('max_booking_days',     '30',      'Maximum hari pemesanan');


-- =========================================================================
-- tb_pemetik — the harvesters (people)
-- =========================================================================
-- Pemetik are a resource managed by the admin. They don't have accounts.
-- Pricing is NOT stored here — it's global via tb_setting and snapshot
-- into each booking.
-- =========================================================================
CREATE TABLE tb_pemetik (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  nama            VARCHAR(100)  NOT NULL,
  deskripsi       TEXT          NULL,
  foto_path       VARCHAR(255)  NULL,
  nomor_telepon   VARCHAR(20)   NULL,
  is_active       TINYINT(1)    NOT NULL DEFAULT 1,
  created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_active (is_active),
  INDEX idx_nama   (nama)
) ENGINE=InnoDB;


-- =========================================================================
-- tb_booking_pemetik — bookings of a pemetik by a user
-- =========================================================================
-- The price per day is SNAPSHOTTED at booking time, so future rate
-- changes don't alter existing bookings.
-- =========================================================================
CREATE TABLE tb_booking_pemetik (
  id                         INT PRIMARY KEY AUTO_INCREMENT,
  user_id                    INT           NOT NULL,
  pemetik_id                 INT           NOT NULL,

  -- Price snapshot (captured at insert time)
  price_per_day_at_booking   DECIMAL(12, 2) NOT NULL,
  total_days                 INT           NOT NULL,
  total_amount               DECIMAL(12, 2) NOT NULL,

  -- Booking window (dates, not datetimes)
  start_date                 DATE          NOT NULL,
  end_date                   DATE          NOT NULL,
  notes                      TEXT          NULL,

  -- Payment
  status                     ENUM(
                               'pending_payment',
                               'paid',
                               'confirmed',
                               'completed',
                               'cancelled'
                             ) NOT NULL DEFAULT 'pending_payment',
  payment_reference          VARCHAR(100)  NULL,
  paid_at                    TIMESTAMP     NULL,

  -- Timestamps
  created_at                 TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  updated_at                 TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id)    REFERENCES tb_user(id)    ON DELETE CASCADE,
  FOREIGN KEY (pemetik_id) REFERENCES tb_pemetik(id) ON DELETE RESTRICT,

  INDEX idx_user    (user_id),
  INDEX idx_pemetik (pemetik_id),
  INDEX idx_status  (status),
  INDEX idx_start   (start_date),

  CHECK (end_date >= start_date),
  CHECK (total_days > 0),
  CHECK (total_amount >= 0)
) ENGINE=InnoDB;


-- migrate:down
DROP TABLE IF EXISTS tb_booking_pemetik;
DROP TABLE IF EXISTS tb_pemetik;
DROP TABLE IF EXISTS tb_setting;