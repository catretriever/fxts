#!/usr/bin/env python3
"""
setup_test_db.py - FXTS test data setup

Creates (or resets) the CSV files in the data/ directory that act as the
database for development and testing.

Usage:
  python3 setup_test_db.py            # create/reset all CSV files
  python3 setup_test_db.py --verify   # show row counts only
  python3 setup_test_db.py --data-dir /path/to/data
"""

import argparse
import csv
import os

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

TABLES = {
    'FXCross': {
        'fields': ['Id', 'FXCross', 'BaseCcy', 'QuoteCcy', 'Scalar', 'IP'],
        'rows': [
            [1, 'GBPJPY', 'GBP', 'JPY', '100.0000', '192.168.1.1'],
            [2, 'EURUSD', 'EUR', 'USD',   '1.0000', '192.168.1.2'],
            [3, 'USDJPY', 'USD', 'JPY', '100.0000', '192.168.1.3'],
            [4, 'GBPUSD', 'GBP', 'USD',   '1.0000', '192.168.1.4'],
            [5, 'AUDUSD', 'AUD', 'USD',   '1.0000', '192.168.1.5'],
        ],
    },
    'HourlyData': {
        'fields': ['Id', 'ticker', 'Date', 'Time', 'Open', 'High', 'Low', 'Close'],
        'rows': [
            [ 1, 'GBPJPY', '2026-03-04', '14:00:00', '190.25000', '190.51000', '190.10000', '190.42000'],
            [ 2, 'GBPJPY', '2026-03-04', '13:00:00', '190.03000', '190.31000', '189.90000', '190.25000'],
            [ 3, 'GBPJPY', '2026-03-04', '12:00:00', '189.78000', '190.10000', '189.65000', '190.03000'],
            [ 4, 'GBPJPY', '2026-03-04', '11:00:00', '189.50000', '189.85000', '189.40000', '189.78000'],
            [ 5, 'GBPJPY', '2026-03-04', '10:00:00', '189.20000', '189.60000', '189.05000', '189.50000'],
            [ 6, 'GBPJPY', '2026-03-04', '09:00:00', '188.90000', '189.30000', '188.75000', '189.20000'],
            [ 7, 'GBPJPY', '2026-03-04', '08:00:00', '188.60000', '189.00000', '188.45000', '188.90000'],
            [ 8, 'GBPJPY', '2026-03-04', '07:00:00', '188.30000', '188.70000', '188.15000', '188.60000'],
            [ 9, 'GBPJPY', '2026-03-04', '06:00:00', '188.00000', '188.40000', '187.90000', '188.30000'],
            [10, 'GBPJPY', '2026-03-04', '05:00:00', '187.75000', '188.10000', '187.65000', '188.00000'],
            [11, 'EURUSD', '2026-03-04', '14:00:00',   '1.08520',   '1.08650',   '1.08440',   '1.08600'],
            [12, 'EURUSD', '2026-03-04', '13:00:00',   '1.08380',   '1.08550',   '1.08320',   '1.08520'],
            [13, 'EURUSD', '2026-03-04', '12:00:00',   '1.08200',   '1.08420',   '1.08150',   '1.08380'],
            [14, 'EURUSD', '2026-03-04', '11:00:00',   '1.08050',   '1.08260',   '1.07980',   '1.08200'],
            [15, 'EURUSD', '2026-03-04', '10:00:00',   '1.07900',   '1.08100',   '1.07830',   '1.08050'],
        ],
    },
    'TEngine': {
        'fields': ['Id', 'TEngine', 'Instrument'],
        'rows': [
            [1, 'GBPJPYeng01', 'GBPJPY'],
            [2, 'EURUSDeng01', 'EURUSD'],
        ],
    },
    'MAP_Pfo_TEngine': {
        'fields': ['Id', 'Portfolio', 'TEngine', 'Weight'],
        'rows': [
            [1, 'FX Portfolio 1', 'GBPJPYeng01', '0.6000'],
            [2, 'FX Portfolio 1', 'EURUSDeng01', '0.4000'],
        ],
    },
    'MAP_TEngine_SigGen': {
        'fields': ['Id', 'TEngine', 'SigGen'],
        'rows': [
            [1, 'GBPJPYeng01', 'GBPJPY_TP_6_7'],
            [2, 'GBPJPYeng01', 'GBPJPY_TP_12_13'],
            [3, 'EURUSDeng01', 'EURUSD_TP_6_7'],
        ],
    },
    'SigGenTP': {
        'fields': ['Id', 'SigGen', 'nMA6', 'nMA6_1'],
        'rows': [
            [1, 'GBPJPY_TP_6_7',    6,  7],
            [2, 'GBPJPY_TP_12_13', 12, 13],
            [3, 'EURUSD_TP_6_7',    6,  7],
        ],
    },
    'fx_table': {
        'fields': ['Id', 'Instrument', 'curncy1', 'curncy2'],
        'rows': [
            [1, 'GBPJPY Curncy', 'GBP', 'JPY'],
            [2, 'EURUSD Curncy', 'EUR', 'USD'],
            [3, 'USDJPY Curncy', 'USD', 'JPY'],
        ],
    },
    'fx_data': {
        'fields': ['Id', 'Instrument', 'TSDate', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_CLOSE'],
        'rows': [
            [1, 'GBPJPY Curncy', '20260304', '188.00000', '190.51000', '187.65000', '190.42000'],
            [2, 'GBPJPY Curncy', '20260303', '187.20000', '188.50000', '186.90000', '188.00000'],
            [3, 'GBPJPY Curncy', '20260228', '186.50000', '187.80000', '186.10000', '187.20000'],
            [4, 'GBPJPY Curncy', '20260227', '185.80000', '186.90000', '185.50000', '186.50000'],
            [5, 'GBPJPY Curncy', '20260226', '185.20000', '186.10000', '184.90000', '185.80000'],
        ],
    },
    'tf_engines': {
        'fields': ['Id', 'Engine', 'Slow', 'Fast', 'Buffer'],
        'rows': [
            [1, 'TF_GBPJPY_32_8',  32,  8, '0.0020'],
            [2, 'TF_GBPJPY_64_16', 64, 16, '0.0030'],
            [3, 'TF_EURUSD_32_8',  32,  8, '0.0010'],
        ],
    },
    # Empty tables — headers only; the app appends rows at runtime
    'futures_data': {
        'fields': ['Id', 'TSDate', 'Instrument_ID', 'NM', 'PX_Open', 'PX_HIGH', 'PX_LOW', 'PX_CLOSE'],
        'rows': [],
    },
    'state_tf_futures': {
        'fields': [
            'Id', 'Instrument', 'Engine', 'TSDate', 'NM', 'FM',
            'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_CLOSE', 'FM_CLOSE',
            'ATR', '20EMA(ATR)', 'EMAFast', 'EMASlow', 'Buffer', 'Sig',
        ],
        'rows': [],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_table(data_dir, name, spec):
    path = os.path.join(data_dir, name + '.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(spec['fields'])
        w.writerows(spec['rows'])


def verify(data_dir):
    print(f"\n{'Table':<25} {'Rows':>6}")
    print('-' * 33)
    for name in TABLES:
        path = os.path.join(data_dir, name + '.csv')
        try:
            with open(path, newline='', encoding='utf-8') as f:
                count = sum(1 for _ in csv.DictReader(f))
        except FileNotFoundError:
            count = -1
        print(f"{name:<25} {count:>6}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_data_dir = os.path.join(here, 'data')

    parser = argparse.ArgumentParser(description='Set up FXTS CSV data files')
    parser.add_argument('--data-dir', default=default_data_dir,
                        help='Directory for CSV files (default: ./data)')
    parser.add_argument('--verify', action='store_true',
                        help='Show row counts only, do not recreate files')
    args = parser.parse_args()

    data_dir = args.data_dir
    os.makedirs(data_dir, exist_ok=True)

    if args.verify:
        print(f"Verifying data directory: {data_dir}")
        verify(data_dir)
    else:
        print(f"Writing CSV files to: {data_dir}")
        for name, spec in TABLES.items():
            write_table(data_dir, name, spec)
            print(f"  {name}.csv  ({len(spec['rows'])} rows)")
        verify(data_dir)

    print("Done.")


if __name__ == '__main__':
    main()
