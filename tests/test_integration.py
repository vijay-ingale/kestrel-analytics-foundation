"""Opt-in PostgreSQL integration tests; only a dedicated test database is accepted."""
import csv
from datetime import date, timedelta
import os
from pathlib import Path

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from pipeline.build import dbt_build
from pipeline.ingest import bootstrap, ingest, REFERENCES

URL = os.environ.get("KESTREL_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="Set KESTREL_TEST_DATABASE_URL to a dedicated /kestrel_test database")


def write_parquet(root, feed, partition, rows, name="part-00000.parquet"):
    directory = root / "raw" / feed / partition
    directory.mkdir(parents=True,exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows),directory / name)


def make_fixture(root):
    ref = root / "reference"
    ref.mkdir(parents=True)
    references = {
        "uom_conversion":[dict(sku_code="S1",eaches_per_case=6,base_uom="EA",case_uom="CS")],
        "warehouse_master":[dict(warehouse_code="WH01",warehouse_name="Test",city="Mumbai",region_name="West",timezone="Asia/Kolkata",chilled_capacity_pallets=10)],
        "carrier_master":[dict(carrier_id="CR1",carrier_name="Test",mode="REEFER",sla_hours=12,rate_per_km=1)],
        "legacy_finance_weekly_report":[dict(week_ending="2025-01-08",channel="MT",gross_sales_inr=999,units_sold=10,basket_count=1,prepared_by="Test",note="Independent")],
        "fiscal_calendar":[],
    }
    for offset in range(304):
        day = date(2025,1,1) + timedelta(days=offset)
        references["fiscal_calendar"].append(dict(calendar_date=day,fiscal_year="FY25" if day.month < 4 else "FY26",fiscal_quarter=f"Q{((day.month-4)%12)//3+1}",fiscal_month_no=(day.month-4)%12+1,iso_week=day.isocalendar().week,day_of_week=day.strftime("%A"),is_weekend=int(day.weekday()>4)))
    for table,fields in REFERENCES.items():
        with (ref / f"{table}.csv").open("w",newline="") as file:
            writer = csv.DictWriter(file,fieldnames=list(fields))
            writer.writeheader()
            writer.writerows(references[table])
    p = dict(txn_id="T1",txn_line_no=1,basket_id="B1",outlet_code="O1",sku_code="S1",channel="MT",event_ts="2025-01-01T20:00:00Z",qty=2,unit_price=10,discount_amount=0,tax_amount=0)
    write_parquet(root,"pos_transactions","ingest_date=2025-01-03",[p,p,dict(p,txn_id="CONFLICT",qty=3),dict(p,txn_id="CONFLICT",qty=4),dict(p,txn_id=None)])
    post = {key:value for key,value in p.items() if key != "qty"}
    post.update(event_ts="2025-10-02T01:00:00Z",quantity_units=2,uom="CS")
    write_parquet(root,"pos_transactions","ingest_date=2025-10-02",[dict(post,txn_id="CASE"),dict(post,txn_id="NO_FACTOR",sku_code="S2"),dict(post,txn_id="EACH",uom="EA",quantity_units=3)])
    t = dict(device_id="D1",telemetry_vendor="COLDEYE",firmware_version="2.1.4",vehicle_registration="V1",route_code="R1",warehouse_code="WH01",gateway_id="GW1",reading_ts="2025-01-01T07:00:00Z",temp_value=50.,temp_unit=None,humidity_pct=50,door_open_flag=0,battery_pct=80,gps_lat=10,gps_lon=70)
    write_parquet(root,"reefer_telemetry","dt=2025-01-01",[t,t,dict(t,device_id="D2",temp_value=None)])
    write_parquet(root,"reefer_telemetry","dt=2025-01-03",[dict(t,reading_ts="2025-01-03T07:00:00Z")])
    corrupt = root / "raw/reefer_telemetry/dt=2025-01-02"
    corrupt.mkdir(parents=True)
    (corrupt / "part-00000.parquet").write_bytes(b"PAR1truncated")
    w = dict(scan_id="SC1",warehouse_code="WH01",event_type="STAGE",order_number="SO1",sku_code="S1",event_ts="2025-01-02 10:00:00",qty_cases=1)
    write_parquet(root,"wms_scan_events","dt=2025-01-02",[w,dict(w,scan_id="SC2",event_type="DISPATCH",event_ts="2025-01-02 11:00:00"),dict(w,scan_id="SC3",order_number="SO2"),dict(w,scan_id="SC4",order_number="SO3",event_ts="2025-01-02 12:00:00"),dict(w,scan_id="SC5",order_number="SO3",event_type="DISPATCH",event_ts="2025-01-02 11:00:00")])
    o = dict(outlet_code="O1",channel="MT",warehouse_code="WH01",__op="I",__op_ts="2024-12-31T00:00:00Z",__seq=1)
    write_parquet(root,"erp_cdc/outlet_master","extract_date=2025-01-01",[o,dict(o,channel="ECOM",__op="U",__op_ts="2025-01-01T19:00:00Z",__seq=2),dict(o,channel="HORECA",__op="U",__op_ts="2025-01-01T19:00:00Z",__seq=100)])
    write_parquet(root,"erp_cdc/product_master","extract_date=2025-01-01",[dict(sku_code="S1",__op="I",__op_ts="2024-12-31T00:00:00Z",__seq=1,case_pack=6)])
    order = dict(order_number="SO1",outlet_code="O1",warehouse_code="WH01",order_date="2025-01-01",source_system="ERP_WEB",order_value_gross=100,__op="I",__op_ts="2025-01-01T00:00:00Z",__seq=1)
    write_parquet(root,"erp_cdc/sales_order_header","extract_date=2025-01-01",[order,dict(order,__op="U",__op_ts="2025-01-02T00:00:00Z",__seq=2),dict(order,__op="D",__seq=100),dict(order,order_number="SO2",source_system="PARTNER_API",order_value_gross=108.5,__seq=3)])
    manifest = root / "_manifest"
    manifest.mkdir()
    with (manifest / "expected_partitions.csv").open("w",newline="") as file:
        writer = csv.DictWriter(file,fieldnames=["feed","partition","file_count","row_count","bytes"])
        writer.writeheader()
        for path in sorted((root / "raw").glob("*/*/*.parquet")):
            if path.parent.name == "dt=2025-01-02" and path.parent.parent.name == "reefer_telemetry":
                count = 3
            else:
                count = pq.ParquetFile(path).metadata.num_rows
            writer.writerow(dict(feed=path.parent.parent.name,partition=path.parent.name,file_count=1,row_count=count,bytes=path.stat().st_size))


def test_pipeline_semantics_and_rerun(tmp_path):
    if not URL.rstrip("/").endswith("/kestrel_test"):
        pytest.fail("Integration database must be named kestrel_test")
    make_fixture(tmp_path)
    with psycopg.connect(URL,autocommit=True) as conn:
        bootstrap(conn)
        for attempt in range(2):
            run_id = conn.execute("INSERT INTO audit.runs(status,data_path) VALUES ('RUNNING',%s) RETURNING run_id",(str(tmp_path),)).fetchone()[0]
            with conn.transaction():
                ingest(conn,tmp_path,run_id,batch_size=2)
            dbt_build(URL)
            conn.execute("UPDATE audit.runs SET status='SUCCESS',finished_at=now() WHERE run_id=%s",(run_id,))
            assert conn.execute("SELECT count(*),sum(gross_sales_inr),sum(units_eaches) FROM analytics.fct_sales").fetchone() == (4,90,15)
            assert conn.execute("SELECT business_date,historical_outlet_channel,unit_status FROM analytics.fct_sales WHERE txn_id='T1'").fetchone() == (date(2025,1,2),"HORECA","MISSING_SOURCE_UOM")
            assert conn.execute("SELECT count(*),count(temperature_c),min(temperature_c) FROM analytics.fct_telemetry").fetchone() == (3,2,10)
            assert conn.execute("SELECT cycle_minutes FROM analytics.mart_warehouse_cycles WHERE order_number='SO1'").fetchone()[0] == 60
            assert conn.execute("SELECT is_deleted,deletion_timestamp_exception FROM analytics.fct_orders WHERE order_number='SO1'").fetchone() == (True,True)
            assert conn.execute("SELECT comparable_order_value_inr FROM analytics.fct_orders WHERE order_number='SO2'").fetchone()[0] == 100
            assert conn.execute("SELECT count(*) FROM audit.quarantine WHERE run_id=%s",(run_id,)).fetchone()[0] == 1
            assert conn.execute("SELECT completeness_status FROM analytics.mart_feed_completeness WHERE feed='reefer_telemetry' AND partition='dt=2025-01-02'").fetchone()[0] == "UNREADABLE_FILE"
            assert conn.execute("SELECT count(*) FROM analytics.mart_key_conflicts").fetchone()[0] == 1
