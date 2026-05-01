"""Smoke: новые ORM-модели импортируются и совместимы с миграцией."""
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_tab_through_orm(db) -> None:
    from portal_api.models.tab import Tab

    tab = Tab(slug="sci-orm", name="Sci ORM", order_idx=42, is_system=False)
    db.add(tab)
    await db.flush()

    found = (await db.execute(
        select(Tab).where(Tab.slug == "sci-orm")
    )).scalar_one()
    assert found.id == tab.id
    assert found.order_idx == 42


@pytest.mark.asyncio
async def test_create_agent_with_tab(db, admin_user) -> None:
    from portal_api.models.agent import Agent
    from portal_api.models.tab import Tab

    tab = Tab(slug="sci-agent", name="Sci", order_idx=0, is_system=False)
    db.add(tab)
    await db.flush()

    agent = Agent(
        slug="echo",
        name="Echo",
        short_description="test",
        tab_id=tab.id,
        enabled=False,
        git_url="https://github.com/x/y.git",
        created_by_user_id=admin_user.id,
    )
    db.add(agent)
    await db.flush()

    found = (await db.execute(
        select(Agent).where(Agent.slug == "echo")
    )).scalar_one()
    assert found.tab_id == tab.id
    assert found.enabled is False
    assert found.current_version_id is None


@pytest.mark.asyncio
async def test_create_agent_version(db, admin_user) -> None:
    from portal_api.models.agent import Agent
    from portal_api.models.agent_version import AgentVersion
    from portal_api.models.tab import Tab

    tab = Tab(slug="sci-v", name="Sci", order_idx=0, is_system=False)
    db.add(tab)
    await db.flush()

    agent = Agent(
        slug="ver-test", name="V", short_description="d",
        tab_id=tab.id, enabled=False, git_url="https://x/y.git",
        created_by_user_id=admin_user.id,
    )
    db.add(agent)
    await db.flush()

    v = AgentVersion(
        agent_id=agent.id,
        git_sha="a" * 40,
        git_ref="main",
        manifest_jsonb={"id": "ver-test", "name": "V", "version": "0.1.0"},
        manifest_version="0.1.0",
        status="pending_build",
        created_by_user_id=admin_user.id,
    )
    db.add(v)
    await db.flush()

    found = (await db.execute(
        select(AgentVersion).where(AgentVersion.agent_id == agent.id)
    )).scalar_one()
    assert found.status == "pending_build"
    assert found.docker_image_tag is None
