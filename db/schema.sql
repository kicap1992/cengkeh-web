/*M!999999\- enable the sandbox mode */
-- MariaDB dump 10.19-11.8.8-MariaDB, for Linux (x86_64)
--
-- Host: db    Database: cengkeh_db
-- ------------------------------------------------------
-- Server version	11.4.13-MariaDB-ubu2404

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `schema_migrations`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `schema_migrations` (
  `version` varchar(128) NOT NULL,
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_follow_option`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_follow_option` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `follow_up_id` int(11) NOT NULL,
  `label` varchar(100) NOT NULL,
  `value` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_follow_option_follow_label` (`follow_up_id`,`label`),
  CONSTRAINT `tb_follow_option_ibfk_1` FOREIGN KEY (`follow_up_id`) REFERENCES `tb_follow_up` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_follow_up`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_follow_up` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pertanyaan_id` int(11) NOT NULL,
  `urutan` int(11) NOT NULL,
  `pertanyaan` text NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_follow_up_pertanyaan_urutan` (`pertanyaan_id`,`urutan`),
  CONSTRAINT `tb_follow_up_ibfk_1` FOREIGN KEY (`pertanyaan_id`) REFERENCES `tb_pertanyaan` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_kategori`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_kategori` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nama` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nama` (`nama`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_keyword`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_keyword` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pertanyaan_id` int(11) NOT NULL,
  `kata` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_keyword_pertanyaan_kata` (`pertanyaan_id`,`kata`),
  KEY `idx_kata` (`kata`),
  CONSTRAINT `tb_keyword_ibfk_1` FOREIGN KEY (`pertanyaan_id`) REFERENCES `tb_pertanyaan` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_option_next_qa`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_option_next_qa` (
  `option_id` int(11) NOT NULL,
  `next_qa_id` int(11) NOT NULL,
  PRIMARY KEY (`option_id`,`next_qa_id`),
  KEY `next_qa_id` (`next_qa_id`),
  CONSTRAINT `tb_option_next_qa_ibfk_1` FOREIGN KEY (`option_id`) REFERENCES `tb_follow_option` (`id`) ON DELETE CASCADE,
  CONSTRAINT `tb_option_next_qa_ibfk_2` FOREIGN KEY (`next_qa_id`) REFERENCES `tb_pertanyaan` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_pertanyaan`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_pertanyaan` (
  `id` int(11) NOT NULL,
  `kategori_id` int(11) NOT NULL,
  `tipe` enum('informational','diagnostic','solution') NOT NULL,
  `pertanyaan` text NOT NULL,
  `jawaban` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `kategori_id` (`kategori_id`),
  CONSTRAINT `tb_pertanyaan_ibfk_1` FOREIGN KEY (`kategori_id`) REFERENCES `tb_kategori` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_pertanyaan_sumber`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_pertanyaan_sumber` (
  `pertanyaan_id` int(11) NOT NULL,
  `sumber_id` int(11) NOT NULL,
  PRIMARY KEY (`pertanyaan_id`,`sumber_id`),
  KEY `sumber_id` (`sumber_id`),
  CONSTRAINT `tb_pertanyaan_sumber_ibfk_1` FOREIGN KEY (`pertanyaan_id`) REFERENCES `tb_pertanyaan` (`id`) ON DELETE CASCADE,
  CONSTRAINT `tb_pertanyaan_sumber_ibfk_2` FOREIGN KEY (`sumber_id`) REFERENCES `tb_sumber` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_relasi`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_relasi` (
  `pertanyaan_id` int(11) NOT NULL,
  `related_id` int(11) NOT NULL,
  PRIMARY KEY (`pertanyaan_id`,`related_id`),
  KEY `related_id` (`related_id`),
  CONSTRAINT `tb_relasi_ibfk_1` FOREIGN KEY (`pertanyaan_id`) REFERENCES `tb_pertanyaan` (`id`) ON DELETE CASCADE,
  CONSTRAINT `tb_relasi_ibfk_2` FOREIGN KEY (`related_id`) REFERENCES `tb_pertanyaan` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_stopwords`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_stopwords` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `kata` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `kata` (`kata`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_sumber`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_sumber` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `kode` varchar(10) NOT NULL,
  `judul` text NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `kode` (`kode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_variasi`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_variasi` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pertanyaan_id` int(11) NOT NULL,
  `teks` text NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_variasi_pertanyaan_teks` (`pertanyaan_id`,`teks`(255)),
  CONSTRAINT `tb_variasi_ibfk_1` FOREIGN KEY (`pertanyaan_id`) REFERENCES `tb_pertanyaan` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'cengkeh_db'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed

--
-- Dbmate schema migrations
--

LOCK TABLES `schema_migrations` WRITE;
INSERT INTO `schema_migrations` (version) VALUES
  ('20261005100000'),
  ('20261005100001'),
  ('20261005162553'),
  ('20261008060834'),
  ('20261010235705');
UNLOCK TABLES;
