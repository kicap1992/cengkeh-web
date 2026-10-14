-- migrate:up

-- =========================================================================
-- Refactor: tb_booking_pemetik → tb_order + tb_booking_pemetik (line items)
-- =========================================================================
-- Rationale:
--   A user can book MULTIPLE pemetik in one transaction. That's one order
--   with N line items, not N separate orders.
--
--   - tb_order        : the transaction (user, dates, total, status, payment)
--   - tb_booking_pemetik : one line per pemetik (price snapshot per line)
--
-- The old tb_booking_pemetik is dropped. It is empty in dev and prod
-- (feature not yet shipped), so no data loss.
-- =========================================================================

DROP TABLE IF EXISTS tb_booking_pemetik;


-- -------------------------------------------------------------------------
-- tb_order — the transaction
-- -------------------------------------------------------------------------
CREATE TABLE tb_order (
  id                INT PRIMARY KEY AUTO_INCREMENT,
  user_id           INT           NOT NULL,
  order_code        VARCHAR(20)   NOT NULL UNIQUE,

  -- Service window (whole order shares one date range)
  start_date        DATE          NOT NULL,
  end_date          DATE          NOT NULL,

  -- Money
  total_amount      DECIMAL(12, 2) NOT NULL,

  -- Payment / lifecycle
  status            ENUM(
                      'pending_payment',
                      'paid',
                      'confirmed',
                      'completed',
                      'cancelled'
                    ) NOT NULL DEFAULT 'pending_payment',
  payment_reference VARCHAR(100)  NULL,
  paid_at           TIMESTAMP     NULL,

  notes             TEXT          NULL,

  created_at        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES tb_user(id) ON DELETE CASCADE,

  INDEX idx_user   (user_id),
  INDEX idx_status (status),
  INDEX idx_start  (start_date),
  INDEX idx_code   (order_code),

  CHECK (end_date >= start_date),
  CHECK (total_amount >= 0)
) ENGINE=InnoDB;


-- -------------------------------------------------------------------------
-- tb_booking_pemetik — line items (one row per pemetik per order)
-- -------------------------------------------------------------------------
CREATE TABLE tb_booking_pemetik (
  id                         INT PRIMARY KEY AUTO_INCREMENT,
  order_id                   INT           NOT NULL,
  pemetik_id                 INT           NOT NULL,

  -- Price snapshot for THIS line (rate at the moment of booking)
  price_per_day_at_booking   DECIMAL(12, 2) NOT NULL,
  total_days                 INT           NOT NULL,
  subtotal                   DECIMAL(12, 2) NOT NULL,

  created_at                 TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (order_id)   REFERENCES tb_order(id)   ON DELETE CASCADE,
  FOREIGN KEY (pemetik_id) REFERENCES tb_pemetik(id) ON DELETE RESTRICT,

  -- Same pemetik can't appear twice in one order
  UNIQUE KEY uq_order_pemetik (order_id, pemetik_id),

  INDEX idx_order   (order_id),
  INDEX idx_pemetik (pemetik_id),

  CHECK (subtotal >= 0),
  CHECK (total_days > 0)
) ENGINE=InnoDB;


-- migrate:down
DROP TABLE IF EXISTS tb_booking_pemetik;
DROP TABLE IF EXISTS tb_order;