-- =============================================================================
-- FXTS Test Database Setup Script  (MariaDB 10.6+)
-- =============================================================================
-- Creates schema and loads sample data for development/testing.
--
-- Quick start:
--   mariadb -u fxts -p FXDB < setup_test_db.sql
--
-- First-time user/database creation (run as root):
--   mariadb -u root -e "
--     CREATE DATABASE IF NOT EXISTS FXDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--     CREATE USER IF NOT EXISTS 'fxts'@'localhost' IDENTIFIED BY 'changeme';
--     GRANT ALL PRIVILEGES ON FXDB.* TO 'fxts'@'localhost';
--     FLUSH PRIVILEGES;"
--
-- Or via setup_test_db.py:
--   python3 setup_test_db.py --user fxts --passwd changeme
-- =============================================================================

-- Create and select database
CREATE DATABASE IF NOT EXISTS FXDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE FXDB;

-- =============================================================================
-- Table: FXCross
-- Defines each FX cross-rate instrument (e.g. GBPJPY).
-- =============================================================================
CREATE TABLE IF NOT EXISTS FXCross (
    Id        INT          NOT NULL AUTO_INCREMENT,
    FXCross   VARCHAR(10)  NOT NULL UNIQUE,
    BaseCcy   VARCHAR(3)   NOT NULL,
    QuoteCcy  VARCHAR(3)   NOT NULL,
    Scalar    DECIMAL(10,4) NOT NULL DEFAULT 1.0,
    IP        VARCHAR(64)  NOT NULL DEFAULT '',
    PRIMARY KEY (Id)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: HourlyData
-- Hourly OHLC price bars for each FX cross.
-- =============================================================================
CREATE TABLE IF NOT EXISTS HourlyData (
    Id      BIGINT        NOT NULL AUTO_INCREMENT,
    ticker  VARCHAR(10)   NOT NULL,
    Date    VARCHAR(10)   NOT NULL,   -- format: YYYY-MM-DD
    Time    VARCHAR(8)    NOT NULL,   -- format: HH:MM:SS
    Open    DECIMAL(12,5) NOT NULL,
    High    DECIMAL(12,5) NOT NULL,
    Low     DECIMAL(12,5) NOT NULL,
    Close   DECIMAL(12,5) NOT NULL,
    PRIMARY KEY (Id),
    INDEX idx_hourly_ticker_date (ticker, Date, Time)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: TEngine
-- A trading engine pairs one instrument with signal generators.
-- =============================================================================
CREATE TABLE IF NOT EXISTS TEngine (
    Id         INT         NOT NULL AUTO_INCREMENT,
    TEngine    VARCHAR(50) NOT NULL UNIQUE,
    Instrument VARCHAR(10) NOT NULL,
    PRIMARY KEY (Id)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: MAP_Pfo_TEngine
-- Maps a named portfolio to one or more trading engines with weights.
-- =============================================================================
CREATE TABLE IF NOT EXISTS MAP_Pfo_TEngine (
    Id        INT          NOT NULL AUTO_INCREMENT,
    Portfolio VARCHAR(100) NOT NULL,
    TEngine   VARCHAR(50)  NOT NULL,
    Weight    DECIMAL(6,4) NOT NULL DEFAULT 1.0,
    PRIMARY KEY (Id),
    INDEX idx_map_pfo (Portfolio)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: MAP_TEngine_SigGen
-- Maps a trading engine to one or more signal generators.
-- =============================================================================
CREATE TABLE IF NOT EXISTS MAP_TEngine_SigGen (
    Id      INT         NOT NULL AUTO_INCREMENT,
    TEngine VARCHAR(50) NOT NULL,
    SigGen  VARCHAR(50) NOT NULL,
    PRIMARY KEY (Id),
    INDEX idx_map_tengine (TEngine)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: SigGenTP
-- Parameters for TP-type signal generators (moving-average crossover).
-- =============================================================================
CREATE TABLE IF NOT EXISTS SigGenTP (
    Id      INT         NOT NULL AUTO_INCREMENT,
    SigGen  VARCHAR(50) NOT NULL UNIQUE,
    nMA6    INT         NOT NULL DEFAULT 6,
    nMA6_1  INT         NOT NULL DEFAULT 7,
    PRIMARY KEY (Id)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: fx_table
-- Active FX pair registry used by data-fetch routines.
-- =============================================================================
CREATE TABLE IF NOT EXISTS fx_table (
    Id         INT        NOT NULL AUTO_INCREMENT,
    Instrument VARCHAR(20) NOT NULL UNIQUE,
    curncy1    VARCHAR(3) NOT NULL,
    curncy2    VARCHAR(3) NOT NULL,
    PRIMARY KEY (Id)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: fx_data
-- Daily OHLC price series for FX instruments.
-- =============================================================================
CREATE TABLE IF NOT EXISTS fx_data (
    Id         BIGINT        NOT NULL AUTO_INCREMENT,
    Instrument VARCHAR(20)   NOT NULL,
    TSDate     VARCHAR(8)    NOT NULL,  -- format: YYYYMMDD
    PX_OPEN    DECIMAL(12,5),
    PX_HIGH    DECIMAL(12,5),
    PX_LOW     DECIMAL(12,5),
    PX_CLOSE   DECIMAL(12,5),
    PRIMARY KEY (Id),
    INDEX idx_fx_data_instr (Instrument, TSDate)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: futures_data
-- Daily OHLC data for futures contracts.
-- =============================================================================
CREATE TABLE IF NOT EXISTS futures_data (
    Id            BIGINT        NOT NULL AUTO_INCREMENT,
    TSDate        VARCHAR(8)    NOT NULL,   -- format: YYYYMMDD
    Instrument_ID VARCHAR(20)   NOT NULL,
    NM            VARCHAR(10)   NOT NULL,   -- delivery code, e.g. Z24
    PX_Open       DECIMAL(12,5),
    PX_HIGH       DECIMAL(12,5),
    PX_LOW        DECIMAL(12,5),
    PX_CLOSE      DECIMAL(12,5),
    PRIMARY KEY (Id),
    INDEX idx_futures_instr (Instrument_ID, NM, TSDate)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: tf_engines
-- Trading-framework engine parameters (EMA fast/slow + buffer).
-- =============================================================================
CREATE TABLE IF NOT EXISTS tf_engines (
    Id     INT         NOT NULL AUTO_INCREMENT,
    Engine VARCHAR(50) NOT NULL UNIQUE,
    Slow   INT         NOT NULL,
    Fast   INT         NOT NULL,
    Buffer DECIMAL(8,4) NOT NULL DEFAULT 0.0,
    PRIMARY KEY (Id)
) ENGINE=InnoDB;

-- =============================================================================
-- Table: state_tf_futures
-- Persists per-bar state for the trend-following engine on futures.
-- =============================================================================
CREATE TABLE IF NOT EXISTS state_tf_futures (
    Id          BIGINT        NOT NULL AUTO_INCREMENT,
    Instrument  VARCHAR(20)   NOT NULL,
    Engine      VARCHAR(50)   NOT NULL,
    TSDate      VARCHAR(8)    NOT NULL,
    NM          VARCHAR(10)   NOT NULL,
    FM          VARCHAR(10)   NOT NULL DEFAULT '',
    PX_OPEN     DECIMAL(12,5),
    PX_HIGH     DECIMAL(12,5),
    PX_LOW      DECIMAL(12,5),
    PX_CLOSE    DECIMAL(12,5),
    FM_CLOSE    DECIMAL(12,5),
    ATR         DECIMAL(12,5),
    `20EMA(ATR)` DECIMAL(12,5),
    EMAFast     DECIMAL(12,5),
    EMASlow     DECIMAL(12,5),
    Buffer      DECIMAL(12,5),
    Sig         INT           NOT NULL DEFAULT 0,
    PRIMARY KEY (Id),
    INDEX idx_state_tf (Instrument, NM, Engine, TSDate)
) ENGINE=InnoDB;

-- =============================================================================
-- Sample Data
-- =============================================================================

-- FX Crosses
INSERT INTO FXCross (FXCross, BaseCcy, QuoteCcy, Scalar, IP) VALUES
    ('GBPJPY',  'GBP', 'JPY', 100.0000, '192.168.1.1'),
    ('EURUSD',  'EUR', 'USD',   1.0000, '192.168.1.2'),
    ('USDJPY',  'USD', 'JPY', 100.0000, '192.168.1.3'),
    ('GBPUSD',  'GBP', 'USD',   1.0000, '192.168.1.4'),
    ('AUDUSD',  'AUD', 'USD',   1.0000, '192.168.1.5');

-- Hourly price data: GBPJPY (10 recent bars, descending so latest first)
INSERT INTO HourlyData (ticker, Date, Time, Open, High, Low, Close) VALUES
    ('GBPJPY', '2026-03-04', '14:00:00', 190.250, 190.510, 190.100, 190.420),
    ('GBPJPY', '2026-03-04', '13:00:00', 190.030, 190.310, 189.900, 190.250),
    ('GBPJPY', '2026-03-04', '12:00:00', 189.780, 190.100, 189.650, 190.030),
    ('GBPJPY', '2026-03-04', '11:00:00', 189.500, 189.850, 189.400, 189.780),
    ('GBPJPY', '2026-03-04', '10:00:00', 189.200, 189.600, 189.050, 189.500),
    ('GBPJPY', '2026-03-04', '09:00:00', 188.900, 189.300, 188.750, 189.200),
    ('GBPJPY', '2026-03-04', '08:00:00', 188.600, 189.000, 188.450, 188.900),
    ('GBPJPY', '2026-03-04', '07:00:00', 188.300, 188.700, 188.150, 188.600),
    ('GBPJPY', '2026-03-04', '06:00:00', 188.000, 188.400, 187.900, 188.300),
    ('GBPJPY', '2026-03-04', '05:00:00', 187.750, 188.100, 187.650, 188.000);

-- Hourly price data: EURUSD
INSERT INTO HourlyData (ticker, Date, Time, Open, High, Low, Close) VALUES
    ('EURUSD', '2026-03-04', '14:00:00', 1.08520, 1.08650, 1.08440, 1.08600),
    ('EURUSD', '2026-03-04', '13:00:00', 1.08380, 1.08550, 1.08320, 1.08520),
    ('EURUSD', '2026-03-04', '12:00:00', 1.08200, 1.08420, 1.08150, 1.08380),
    ('EURUSD', '2026-03-04', '11:00:00', 1.08050, 1.08260, 1.07980, 1.08200),
    ('EURUSD', '2026-03-04', '10:00:00', 1.07900, 1.08100, 1.07830, 1.08050);

-- Trading Engines
INSERT INTO TEngine (TEngine, Instrument) VALUES
    ('GBPJPYeng01', 'GBPJPY'),
    ('EURUSDeng01', 'EURUSD');

-- Portfolio → Engine mappings
INSERT INTO MAP_Pfo_TEngine (Portfolio, TEngine, Weight) VALUES
    ('FX Portfolio 1', 'GBPJPYeng01', 0.6000),
    ('FX Portfolio 1', 'EURUSDeng01', 0.4000);

-- Engine → Signal Generator mappings
INSERT INTO MAP_TEngine_SigGen (TEngine, SigGen) VALUES
    ('GBPJPYeng01', 'GBPJPY_TP_6_7'),
    ('GBPJPYeng01', 'GBPJPY_TP_12_13'),
    ('EURUSDeng01', 'EURUSD_TP_6_7');

-- TP Signal Generator parameters
INSERT INTO SigGenTP (SigGen, nMA6, nMA6_1) VALUES
    ('GBPJPY_TP_6_7',   6,  7),
    ('GBPJPY_TP_12_13', 12, 13),
    ('EURUSD_TP_6_7',   6,  7);

-- Active FX pairs registry
INSERT INTO fx_table (Instrument, curncy1, curncy2) VALUES
    ('GBPJPY Curncy', 'GBP', 'JPY'),
    ('EURUSD Curncy', 'EUR', 'USD'),
    ('USDJPY Curncy', 'USD', 'JPY');

-- Daily FX data (GBPJPY, last 5 days)
INSERT INTO fx_data (Instrument, TSDate, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE) VALUES
    ('GBPJPY Curncy', '20260304', 188.000, 190.510, 187.650, 190.420),
    ('GBPJPY Curncy', '20260303', 187.200, 188.500, 186.900, 188.000),
    ('GBPJPY Curncy', '20260228', 186.500, 187.800, 186.100, 187.200),
    ('GBPJPY Curncy', '20260227', 185.800, 186.900, 185.500, 186.500),
    ('GBPJPY Curncy', '20260226', 185.200, 186.100, 184.900, 185.800);

-- TF engine parameters
INSERT INTO tf_engines (Engine, Slow, Fast, Buffer) VALUES
    ('TF_GBPJPY_32_8',  32, 8,  0.0020),
    ('TF_GBPJPY_64_16', 64, 16, 0.0030),
    ('TF_EURUSD_32_8',  32, 8,  0.0010);

-- =============================================================================
-- Verification queries (run after setup to confirm data loaded correctly)
-- =============================================================================
-- SELECT 'FXCross'          AS tbl, COUNT(*) AS rows FROM FXCross
-- UNION ALL
-- SELECT 'HourlyData',        COUNT(*) FROM HourlyData
-- UNION ALL
-- SELECT 'TEngine',           COUNT(*) FROM TEngine
-- UNION ALL
-- SELECT 'MAP_Pfo_TEngine',   COUNT(*) FROM MAP_Pfo_TEngine
-- UNION ALL
-- SELECT 'MAP_TEngine_SigGen',COUNT(*) FROM MAP_TEngine_SigGen
-- UNION ALL
-- SELECT 'SigGenTP',          COUNT(*) FROM SigGenTP
-- UNION ALL
-- SELECT 'fx_table',          COUNT(*) FROM fx_table
-- UNION ALL
-- SELECT 'fx_data',           COUNT(*) FROM fx_data
-- UNION ALL
-- SELECT 'tf_engines',        COUNT(*) FROM tf_engines;
