"""
FastAPI application for Financial Mind-Map OS.

Exposes the Python engine over HTTP so the web UI can drive a sync, read the
current Action Report, resolve items (Approve/Deny/Snooze), render the financial
mind-map, and enter data manually (until a bank aggregator is wired in).

The database connection is per-request; the schema is migrated once at startup.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src import actions, db
from src.api.schemas import (
    AccountCreate,
    BillCreate,
    MemberCreate,
    PaycheckScheduleCreate,
    ResolveRequest,
    TransactionCreate,
)
from src.sync.engine import heartbeat
from src.visualization import build_map_from_db

# Path to a built frontend bundle (Phase 2). Served at "/" when present.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def get_db() -> Iterator[sqlite3.Connection]:
    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _report_payload(conn: sqlite3.Connection, report: sqlite3.Row | None) -> dict | None:
    if report is None:
        return None
    items = db.get_action_items(conn, report["id"])
    return {"report": dict(report), "items": db.coerce_rows(items)}


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    db.migrate()  # ensure the schema exists before serving requests
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Financial Mind-Map OS", version="0.1.0", lifespan=_lifespan)

    # Local-first dev: the UI may run on a different port (Vite).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health -------------------------------------------------------
    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.1.0"}

    # --- Sync & reports ----------------------------------------------
    @app.post("/api/sync")
    def sync(conn: sqlite3.Connection = Depends(get_db)) -> dict:
        return heartbeat(conn, today=date.today())

    @app.get("/api/report/latest")
    def latest_report(conn: sqlite3.Connection = Depends(get_db)) -> dict:
        payload = _report_payload(conn, db.get_latest_report(conn))
        if payload is None:
            return {"report": None, "items": []}
        return payload

    @app.post("/api/items/{item_id}/resolve")
    def resolve_item(
        item_id: int,
        body: ResolveRequest,
        conn: sqlite3.Connection = Depends(get_db),
    ) -> dict:
        try:
            row = actions.resolve_action_item(
                conn, item_id, body.resolution, snooze_days=body.snooze_days
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return dict(row)

    # --- Mind map -----------------------------------------------------
    @app.get("/api/graph")
    def graph(conn: sqlite3.Connection = Depends(get_db)) -> dict:
        return build_map_from_db(conn).to_graph_data()

    # --- Read collections --------------------------------------------
    @app.get("/api/accounts")
    def list_accounts(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
        return db.coerce_rows(db.get_accounts(conn))

    @app.get("/api/bills")
    def list_bills(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
        return db.coerce_rows(db.get_bills(conn, active_only=False))

    @app.get("/api/subscriptions")
    def list_subscriptions(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
        return db.coerce_rows(db.get_subscriptions(conn))

    @app.get("/api/members")
    def list_members(conn: sqlite3.Connection = Depends(get_db)) -> list[dict]:
        return db.coerce_rows(db.get_members(conn))

    # --- Manual data entry -------------------------------------------
    @app.post("/api/members", status_code=201)
    def create_member(
        body: MemberCreate, conn: sqlite3.Connection = Depends(get_db)
    ) -> dict:
        member_hash = db.hash_pii(body.member_id)
        db.upsert_member(
            conn,
            member_hash,
            role=body.role,
            spending_limit=body.spending_limit,
            baseline_monthly=body.baseline_monthly,
        )
        return {"member_hash": member_hash}

    @app.post("/api/accounts", status_code=201)
    def create_account(
        body: AccountCreate, conn: sqlite3.Connection = Depends(get_db)
    ) -> dict:
        account_hash = db.hash_pii(body.account_id)
        db.upsert_account(
            conn,
            account_hash,
            name=body.name,
            bucket_type=body.bucket_type,
            balance=body.balance,
            member_hash=db.hash_pii(body.member_id) if body.member_id else None,
        )
        return {"account_hash": account_hash}

    @app.post("/api/bills", status_code=201)
    def create_bill(
        body: BillCreate, conn: sqlite3.Connection = Depends(get_db)
    ) -> dict:
        bill_id = db.insert_bill(
            conn,
            db.hash_pii(body.merchant),
            amount=body.amount,
            due_day=body.due_day,
            label=body.label,
            grace_period_days=body.grace_period_days,
            late_fee=body.late_fee,
            category=body.category,
            auto_pay=body.auto_pay,
        )
        return {"id": bill_id}

    @app.post("/api/transactions", status_code=201)
    def create_transaction(
        body: TransactionCreate, conn: sqlite3.Connection = Depends(get_db)
    ) -> dict:
        txn_id = db.insert_transaction(
            conn,
            account_hash=db.hash_pii(body.account_id),
            amount=body.amount,
            date=body.date,
            merchant_hash=db.hash_pii(body.merchant) if body.merchant else None,
            member_hash=db.hash_pii(body.member_id) if body.member_id else None,
            description_tokens=(
                db.tokenize_description(body.description) if body.description else None
            ),
            bucket_type=body.bucket_type,
        )
        return {"id": txn_id}

    @app.post("/api/paycheck-schedules", status_code=201)
    def create_schedule(
        body: PaycheckScheduleCreate, conn: sqlite3.Connection = Depends(get_db)
    ) -> dict:
        schedule_id = db.insert_paycheck_schedule(
            conn,
            db.hash_pii(body.member_id),
            pay_day_1=body.pay_day_1,
            pay_day_2=body.pay_day_2,
            pay_amount=body.pay_amount,
        )
        return {"id": schedule_id}

    # --- Frontend (served when a build exists) -----------------------
    if _FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()
