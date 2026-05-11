"""Admin audit log: write через invite endpoint + read через GET /api/admin/audit."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal_api.models import AdminAuditLog


@pytest.mark.asyncio
async def test_invite_create_writes_audit_row(
    admin_client: AsyncClient, db: AsyncSession,
) -> None:
    resp = await admin_client.post(
        "/api/admin/invites",
        json={"email": "newcomer@example.com"},
    )
    assert resp.status_code == 201, resp.text

    rows = (
        await db.execute(
            select(AdminAuditLog).where(AdminAuditLog.action == "invite.create")
        )
    ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.resource_type == "invite"
    assert row.payload_jsonb == {"email": "newcomer@example.com"}
    assert row.actor_user_id is not None


@pytest.mark.asyncio
async def test_invite_revoke_writes_audit_row(
    admin_client: AsyncClient, db: AsyncSession,
) -> None:
    create_resp = await admin_client.post(
        "/api/admin/invites",
        json={"email": "to-revoke@example.com"},
    )
    invite_id = create_resp.json()["id"]

    revoke_resp = await admin_client.delete(f"/api/admin/invites/{invite_id}")
    assert revoke_resp.status_code == 200

    rows = (
        await db.execute(
            select(AdminAuditLog).where(AdminAuditLog.action == "invite.revoke")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].resource_id == str(invite_id)


@pytest.mark.asyncio
async def test_admin_audit_endpoint_lists_rows(admin_client: AsyncClient) -> None:
    for email in ("a@x.io", "b@x.io", "c@x.io"):
        await admin_client.post("/api/admin/invites", json={"email": email})

    resp = await admin_client.get("/api/admin/audit?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 3
    assert all("created_at" in r for r in body)
    actions = {r["action"] for r in body}
    assert "invite.create" in actions


@pytest.mark.asyncio
async def test_admin_audit_filter_by_action(admin_client: AsyncClient) -> None:
    await admin_client.post("/api/admin/invites", json={"email": "filter@x.io"})

    resp = await admin_client.get("/api/admin/audit?action=invite.create")
    assert resp.status_code == 200
    body = resp.json()
    assert all(r["action"] == "invite.create" for r in body)


@pytest.mark.asyncio
async def test_admin_audit_requires_admin(user_client: AsyncClient) -> None:
    resp = await user_client.get("/api/admin/audit")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_audit_pagination(admin_client: AsyncClient) -> None:
    for i in range(7):
        await admin_client.post("/api/admin/invites", json={"email": f"p{i}@x.io"})

    p1 = (await admin_client.get("/api/admin/audit?limit=3")).json()
    assert len(p1) == 3
    p2 = (await admin_client.get(f"/api/admin/audit?limit=3&before={p1[-1]['id']}")).json()
    assert len(p2) >= 1
    ids_p1 = {r["id"] for r in p1}
    assert all(r["id"] not in ids_p1 for r in p2)


@pytest.mark.asyncio
async def test_admin_audit_invalid_limit(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/admin/audit?limit=999")
    assert resp.status_code == 400
