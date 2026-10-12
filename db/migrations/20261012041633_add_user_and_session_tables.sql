-- migrate:up

-- =========================================================================
-- tb_user — user accounts (both pending registration and active users)
-- =========================================================================
-- status values:
--   pending   — just registered, awaiting admin approval
--   active    — approved, can log in
--   rejected  — admin declined the registration
--   suspended — previously active, now disabled (e.g., abuse, deactivation)
-- =========================================================================
CREATE TABLE tb_user (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  nomor_telepon   VARCHAR(20)  NOT NULL UNIQUE,
  nama            VARCHAR(100) NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  level           ENUM('user','admin') NOT NULL DEFAULT 'user',
  status          ENUM('pending','active','rejected','suspended')
                    NOT NULL DEFAULT 'pending',
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
  last_login_at   TIMESTAMP NULL,
  INDEX idx_status (status),
  INDEX idx_level (level)
) ENGINE=InnoDB;


-- =========================================================================
-- tb_session — server-side login sessions
-- =========================================================================
-- Each row is one active login session. When the user logs out,
-- or when the session expires, the row is deleted.
--
-- To invalidate all sessions for a user (e.g., password change),
-- simply DELETE FROM tb_session WHERE user_id = <id>.
-- =========================================================================
CREATE TABLE tb_session (
  id           CHAR(36)     PRIMARY KEY,       -- UUID v4
  user_id      INT          NOT NULL,
  created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  expires_at   TIMESTAMP    NOT NULL,
  ip_address   VARCHAR(45),                    -- IPv4 or IPv6
  user_agent   VARCHAR(255),
  FOREIGN KEY (user_id) REFERENCES tb_user(id) ON DELETE CASCADE,
  INDEX idx_expires (expires_at),
  INDEX idx_user (user_id)
) ENGINE=InnoDB;


-- migrate:down
DROP TABLE IF EXISTS tb_session;
DROP TABLE IF EXISTS tb_user;