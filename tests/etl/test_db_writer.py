"""Tests for db_writer.py: schema creation, insertion, and FK/PK constraint enforcement."""

import os
import sqlite3
import sys
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "etl"))

from db_writer import init_database, insert_dataframe, table_row_count

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "src", "etl", "schema.sql")


@pytest.fixture()
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    init_database(path, SCHEMA_PATH)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_init_database_creates_10_tables(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()
    expected = {"companies", "profitandloss", "balancesheet", "cashflow", "analysis",
                "documents", "prosandcons", "sectors", "stock_prices", "market_cap"}
    assert expected.issubset(tables)


def test_insert_companies_round_trip(db_path):
    df = pd.DataFrame({
        "id": ["TCS", "INFY"], "company_name": ["Tata Consultancy Services", "Infosys"],
        "face_value": [1, 5],
    })
    rows_inserted = insert_dataframe("companies", df, db_path)
    assert rows_inserted == 2
    assert table_row_count("companies", db_path) == 2


def test_fk_violation_is_rejected(db_path):
    companies = pd.DataFrame({"id": ["TCS"], "company_name": ["TCS"], "face_value": [1]})
    insert_dataframe("companies", companies, db_path)

    orphan_pl = pd.DataFrame({
        "company_id": ["GHOST"], "year": ["2023-03"], "sales": [100],
        "expenses": [80], "operating_profit": [20], "opm_percentage": [20.0],
    })
    with pytest.raises(sqlite3.IntegrityError):
        insert_dataframe("profitandloss", orphan_pl, db_path)


def test_duplicate_company_year_pk_is_rejected(db_path):
    companies = pd.DataFrame({"id": ["TCS"], "company_name": ["TCS"], "face_value": [1]})
    insert_dataframe("companies", companies, db_path)

    pl = pd.DataFrame({
        "company_id": ["TCS"], "year": ["2023-03"], "sales": [100],
        "expenses": [80], "operating_profit": [20], "opm_percentage": [20.0],
    })
    insert_dataframe("profitandloss", pl, db_path)
    with pytest.raises(sqlite3.IntegrityError):
        insert_dataframe("profitandloss", pl, db_path)


def test_valid_pl_insert_succeeds(db_path):
    companies = pd.DataFrame({"id": ["TCS"], "company_name": ["TCS"], "face_value": [1]})
    insert_dataframe("companies", companies, db_path)

    pl = pd.DataFrame({
        "company_id": ["TCS"], "year": ["2023-03"], "sales": [225458],
        "expenses": [176924], "operating_profit": [48534], "opm_percentage": [21.5],
    })
    rows_inserted = insert_dataframe("profitandloss", pl, db_path)
    assert rows_inserted == 1
    assert table_row_count("profitandloss", db_path) == 1