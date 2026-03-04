-- FXTS Database Setup Script
-- Creates the FXDB database, user, and all required tables with sample data

-- Create database
CREATE DATABASE IF NOT EXISTS FXDB;

-- Create user and grant privileges
CREATE USER IF NOT EXISTS 'matt'@'localhost' IDENTIFIED BY 'matt';
GRANT ALL PRIVILEGES ON FXDB.* TO 'matt'@'localhost';
FLUSH PRIVILEGES;

USE FXDB;

-- ---------------------------------------------------------------------------
-- FXCross: currency pair definitions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS FXCross (
    Id        INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    FXCross   VARCHAR(20)  NOT NULL UNIQUE,
    BaseCcy   VARCHAR(3)   NOT NULL,
    QuoteCcy  VARCHAR(3)   NOT NULL,
    Scalar    DECIMAL(10,4) NOT NULL DEFAULT 1.0,
    IP        DECIMAL(10,4) NOT NULL DEFAULT 0.0
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO FXCross (FXCross, BaseCcy, QuoteCcy, Scalar, IP) VALUES
    ('GBPJPY', 'GBP', 'JPY', 1.0, 0.01),
    ('EURUSD', 'EUR', 'USD', 1.0, 0.0001),
    ('USDJPY', 'USD', 'JPY', 1.0, 0.01),
    ('GBPUSD', 'GBP', 'USD', 1.0, 0.0001);

-- ---------------------------------------------------------------------------
-- HourlyData: hourly OHLC price bars
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS HourlyData (
    Id     INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(20)  NOT NULL,
    Date   DATE         NOT NULL,
    Time   TIME         NOT NULL,
    Open   DECIMAL(12,4) NOT NULL,
    High   DECIMAL(12,4) NOT NULL,
    Low    DECIMAL(12,4) NOT NULL,
    Close  DECIMAL(12,4) NOT NULL,
    INDEX idx_ticker_date_time (ticker, Date DESC, Time DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Sample GBPJPY hourly data (recent representative bars)
INSERT IGNORE INTO HourlyData (ticker, Date, Time, Open, High, Low, Close) VALUES
    ('GBPJPY', '2002-02-05', '14:00:00', 189.44, 189.84, 189.30, 189.84),
    ('GBPJPY', '2002-02-05', '13:00:00', 189.10, 189.50, 188.90, 189.44),
    ('GBPJPY', '2002-02-05', '12:00:00', 188.75, 189.20, 188.60, 189.10),
    ('GBPJPY', '2002-02-05', '11:00:00', 188.30, 188.90, 188.10, 188.75),
    ('GBPJPY', '2002-02-05', '10:00:00', 187.95, 188.50, 187.80, 188.30),
    ('GBPJPY', '2002-02-04', '17:00:00', 187.60, 188.10, 187.40, 187.95),
    ('GBPJPY', '2002-02-04', '16:00:00', 187.20, 187.75, 187.00, 187.60),
    ('GBPJPY', '2002-02-04', '15:00:00', 186.90, 187.40, 186.70, 187.20),
    ('GBPJPY', '2002-02-04', '14:00:00', 186.55, 187.05, 186.35, 186.90),
    ('GBPJPY', '2002-02-04', '13:00:00', 186.20, 186.70, 186.00, 186.55);

-- ---------------------------------------------------------------------------
-- fx_table: active FX pairs metadata
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fx_table (
    Id         INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Instrument VARCHAR(20) NOT NULL UNIQUE,
    curncy1    VARCHAR(3)  NOT NULL,
    curncy2    VARCHAR(3)  NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO fx_table (Instrument, curncy1, curncy2) VALUES
    ('GBPJPY', 'GBP', 'JPY'),
    ('EURUSD', 'EUR', 'USD'),
    ('USDJPY', 'USD', 'JPY'),
    ('GBPUSD', 'GBP', 'USD');

-- ---------------------------------------------------------------------------
-- fx_data: daily FX historical price data
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fx_data (
    Id         INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Instrument VARCHAR(20)   NOT NULL,
    TSDate     CHAR(8)       NOT NULL,   -- YYYYMMDD format
    PX_OPEN    DECIMAL(12,4) NOT NULL,
    PX_HIGH    DECIMAL(12,4) NOT NULL,
    PX_LOW     DECIMAL(12,4) NOT NULL,
    PX_CLOSE   DECIMAL(12,4) NOT NULL,
    UNIQUE KEY uk_instr_date (Instrument, TSDate),
    INDEX idx_instrument (Instrument)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO fx_data (Instrument, TSDate, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE) VALUES
    ('GBPJPY', '20020205', 189.44, 189.84, 187.80, 189.84),
    ('GBPJPY', '20020204', 186.20, 188.10, 186.00, 187.95),
    ('GBPJPY', '20020201', 185.50, 186.50, 185.10, 186.20);

-- ---------------------------------------------------------------------------
-- futures_data: futures market OHLC data
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS futures_data (
    Id            INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Instrument_ID VARCHAR(20)   NOT NULL,
    NM            VARCHAR(20)   NOT NULL,   -- delivery / contract code
    TSDate        CHAR(8)       NOT NULL,   -- YYYYMMDD format
    PX_Open       DECIMAL(12,4),
    PX_HIGH       DECIMAL(12,4),
    PX_LOW        DECIMAL(12,4),
    PX_CLOSE      DECIMAL(12,4),
    UNIQUE KEY uk_instr_nm_date (Instrument_ID, NM, TSDate),
    INDEX idx_instrument_nm (Instrument_ID, NM)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ---------------------------------------------------------------------------
-- state_tf_futures: trend-following engine state per bar
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS state_tf_futures (
    Id           INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Instrument   VARCHAR(20)   NOT NULL,
    Engine       VARCHAR(50)   NOT NULL,
    TSDate       CHAR(8)       NOT NULL,
    NM           VARCHAR(20)   NOT NULL,
    FM           DECIMAL(12,4),
    PX_OPEN      DECIMAL(12,4),
    PX_HIGH      DECIMAL(12,4),
    PX_LOW       DECIMAL(12,4),
    PX_CLOSE     DECIMAL(12,4),
    FM_CLOSE     DECIMAL(12,4),
    ATR          DECIMAL(12,4),
    `20EMA(ATR)` DECIMAL(12,4),
    EMAFast      DECIMAL(12,4),
    EMASlow      DECIMAL(12,4),
    Buffer       DECIMAL(12,4),
    Sig          DECIMAL(6,2),
    UNIQUE KEY uk_instr_engine_nm_date (Instrument, Engine, NM, TSDate),
    INDEX idx_instr_engine (Instrument, Engine)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ---------------------------------------------------------------------------
-- TEngine: trading engine definitions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS TEngine (
    Id         INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    TEngine    VARCHAR(50) NOT NULL UNIQUE,
    Instrument VARCHAR(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO TEngine (TEngine, Instrument) VALUES
    ('GBPJPY', 'GBPJPY');

-- ---------------------------------------------------------------------------
-- MAP_Pfo_TEngine: portfolio → trading engine mappings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS MAP_Pfo_TEngine (
    Id        INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Portfolio VARCHAR(100)  NOT NULL,
    TEngine   VARCHAR(50)   NOT NULL,
    Weight    DECIMAL(8,4)  NOT NULL DEFAULT 1.0,
    INDEX idx_portfolio (Portfolio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO MAP_Pfo_TEngine (Portfolio, TEngine, Weight) VALUES
    ('FX Portfolio 1', 'GBPJPY', 1.0);

-- ---------------------------------------------------------------------------
-- MAP_TEngine_SigGen: trading engine → signal generator mappings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS MAP_TEngine_SigGen (
    Id      INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    TEngine VARCHAR(50) NOT NULL,
    SigGen  VARCHAR(50) NOT NULL,
    INDEX idx_tengine (TEngine)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO MAP_TEngine_SigGen (TEngine, SigGen) VALUES
    ('GBPJPY', 'GBPJPY_TP6');

-- ---------------------------------------------------------------------------
-- SigGenTP: technical-pattern signal generator parameters
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SigGenTP (
    Id     INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    SigGen VARCHAR(50) NOT NULL UNIQUE,
    nMA6   INT         NOT NULL DEFAULT 6,
    nMA6_1 INT         NOT NULL DEFAULT 7
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO SigGenTP (SigGen, nMA6, nMA6_1) VALUES
    ('GBPJPY_TP6', 6, 7);

-- ---------------------------------------------------------------------------
-- tf_engines: trend-following engine parameter sets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tf_engines (
    Id     INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Engine VARCHAR(50) NOT NULL UNIQUE,
    Slow   INT         NOT NULL,
    Fast   INT         NOT NULL,
    Buffer DECIMAL(8,4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT IGNORE INTO tf_engines (Engine, Slow, Fast, Buffer) VALUES
    ('TF_100_20_05', 100, 20, 0.5),
    ('TF_200_50_05', 200, 50, 0.5),
    ('TF_50_10_025', 50,  10, 0.25);
