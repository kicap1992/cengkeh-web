-- migrate:up

-- =========================================================================
-- Add cancel_reason to tb_order
-- =========================================================================
-- Why: when an order is cancelled — by admin, by user, or automatically
-- because a conflicting order got confirmed first (first-paid-first-served)
-- — we need to record WHY. Shown in the admin penyewaan list and to the user.
-- =========================================================================

ALTER TABLE tb_order
  ADD COLUMN cancel_reason VARCHAR(255) NULL DEFAULT NULL AFTER status;

-- migrate:down

ALTER TABLE tb_order
  DROP COLUMN cancel_reason;