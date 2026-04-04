"""
Tests for multi-tenant PostgreSQL schema with Row-Level Security.
Verifies that tenants can NEVER access each other's data.
"""

import uuid

import pytest
from sqlalchemy import text

from tests.conftest import TENANT_A_ID, TENANT_B_ID, USER_A_ID, USER_B_ID


# ────────────────────────────────────────────────────────────────────
# RLS Isolation Tests
# ────────────────────────────────────────────────────────────────────


class TestRLSIsolation:
    """Verify row-level security prevents cross-tenant data access."""

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_read_tenant_b_users(self, db_session):
        """Tenant A context should only see Tenant A's users."""
        await db_session.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"), {"tid": str(TENANT_A_ID)}
        )
        result = await db_session.execute(text("SELECT id, email FROM users"))
        rows = result.fetchall()
        user_ids = [row[0] for row in rows]

        assert USER_A_ID in user_ids, "Tenant A should see its own user"
        assert USER_B_ID not in user_ids, "Tenant A must NOT see Tenant B's user"

    @pytest.mark.asyncio
    async def test_tenant_b_cannot_read_tenant_a_users(self, db_session):
        """Tenant B context should only see Tenant B's users."""
        await db_session.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"), {"tid": str(TENANT_B_ID)}
        )
        result = await db_session.execute(text("SELECT id, email FROM users"))
        rows = result.fetchall()
        user_ids = [row[0] for row in rows]

        assert USER_B_ID in user_ids, "Tenant B should see its own user"
        assert USER_A_ID not in user_ids, "Tenant B must NOT see Tenant A's user"

    @pytest.mark.asyncio
    async def test_tenant_cannot_insert_with_other_tenant_id(self, db_session):
        """Tenant A should not be able to insert a row with Tenant B's ID."""
        await db_session.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"), {"tid": str(TENANT_A_ID)}
        )
        with pytest.raises(Exception):
            await db_session.execute(
                text(
                    "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
                    "VALUES (:id, :tid, :email, :name, :role, :pw)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tid": str(TENANT_B_ID),  # Wrong tenant!
                    "email": "hacker@evil.com",
                    "name": "Hacker",
                    "role": "viewer",
                    "pw": "$2b$12$fake",
                },
            )
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_rls_applies_to_agent_actions(self, db_session):
        """Agent actions should be isolated per tenant."""
        # Insert an action for Tenant A (as Tenant A)
        await db_session.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"), {"tid": str(TENANT_A_ID)}
        )
        action_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO agent_actions "
                "(id, tenant_id, agent_type, action_type, status, proposed_change, reasoning, confidence_score) "
                "VALUES (:id, :tid, 'listing', 'update_title', 'proposed', '{}'::jsonb, 'test', 0.95)"
            ),
            {"id": str(action_id), "tid": str(TENANT_A_ID)},
        )

        # Switch to Tenant B — should see zero actions
        await db_session.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"), {"tid": str(TENANT_B_ID)}
        )
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM agent_actions")
        )
        count = result.scalar()
        assert count == 0, "Tenant B must NOT see Tenant A's agent actions"

    @pytest.mark.asyncio
    async def test_rls_policies_exist_on_all_tenant_tables(self, db_session):
        """Every table with a tenant_id column must have an RLS policy."""
        result = await db_session.execute(
            text(
                """
                SELECT c.relname AS table_name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid
                WHERE n.nspname = 'public'
                  AND a.attname = 'tenant_id'
                  AND c.relkind = 'r'
                  AND NOT EXISTS (
                      SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid
                  )
                """
            )
        )
        tables_without_policy = [row[0] for row in result.fetchall()]
        # audit_log has tenant_id but is exempt from RLS
        tables_without_policy = [
            t for t in tables_without_policy if t != "audit_log"
        ]
        assert (
            tables_without_policy == []
        ), f"Tables missing RLS policy: {tables_without_policy}"

    @pytest.mark.asyncio
    async def test_rls_is_enabled_not_just_defined(self, db_session):
        """RLS must be ENABLED (relrowsecurity=true) on tenant tables."""
        result = await db_session.execute(
            text(
                """
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid
                WHERE n.nspname = 'public'
                  AND a.attname = 'tenant_id'
                  AND c.relkind = 'r'
                  AND c.relname != 'audit_log'
                  AND c.relrowsecurity = false
                """
            )
        )
        tables_without_rls = [row[0] for row in result.fetchall()]
        assert (
            tables_without_rls == []
        ), f"Tables with RLS defined but NOT enabled: {tables_without_rls}"


# ────────────────────────────────────────────────────────────────────
# Audit Log Tests
# ────────────────────────────────────────────────────────────────────


class TestAuditLog:
    """Verify the audit trigger logs INSERT/UPDATE/DELETE."""

    @pytest.mark.asyncio
    async def test_insert_creates_audit_entry(self, db_session):
        """Inserting a user should create an audit_log entry with new_data."""
        await db_session.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"), {"tid": str(TENANT_A_ID)}
        )
        new_user_id = uuid.uuid4()
        await db_session.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
                "VALUES (:id, :tid, :email, :name, :role, :pw)"
            ),
            {
                "id": str(new_user_id),
                "tid": str(TENANT_A_ID),
                "email": "audit-test-insert@tenant-a.com",
                "name": "Audit Insert",
                "role": "viewer",
                "pw": "$2b$12$audit_hash",
            },
        )

        result = await db_session.execute(
            text(
                "SELECT operation, new_data FROM audit_log "
                "WHERE table_name = 'users' AND row_id = :rid "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"rid": str(new_user_id)},
        )
        row = result.fetchone()
        assert row is not None, "Audit log entry should exist for INSERT"
        assert row[0] == "INSERT", "Operation should be INSERT"
        assert row[1] is not None, "new_data should contain the inserted row"

    @pytest.mark.asyncio
    async def test_update_creates_audit_entry(self, db_session):
        """Updating a user name should create an audit_log entry with old+new data."""
        await db_session.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"), {"tid": str(TENANT_A_ID)}
        )
        # Update User A's name
        await db_session.execute(
            text("UPDATE users SET name = 'Alice Updated' WHERE id = :uid"),
            {"uid": str(USER_A_ID)},
        )

        result = await db_session.execute(
            text(
                "SELECT operation, old_data, new_data FROM audit_log "
                "WHERE table_name = 'users' AND row_id = :rid AND operation = 'UPDATE' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"rid": str(USER_A_ID)},
        )
        row = result.fetchone()
        assert row is not None, "Audit log entry should exist for UPDATE"
        assert row[0] == "UPDATE", "Operation should be UPDATE"
        assert row[1] is not None, "old_data should contain previous row state"
        assert row[2] is not None, "new_data should contain updated row state"


# ────────────────────────────────────────────────────────────────────
# Migration / Schema Tests
# ────────────────────────────────────────────────────────────────────


class TestMigrations:
    """Verify the migration created all expected tables and columns."""

    @pytest.mark.asyncio
    async def test_all_expected_tables_exist(self, db_session):
        """All required tables should exist in the public schema."""
        expected_tables = {
            "tenants",
            "users",
            "amazon_connections",
            "agent_actions",
            "approval_queue",
            "notification_log",
            "audit_log",
        }
        result = await db_session.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        )
        existing_tables = {row[0] for row in result.fetchall()}
        missing = expected_tables - existing_tables
        assert missing == set(), f"Missing tables: {missing}"

    @pytest.mark.asyncio
    async def test_tenants_table_columns(self, db_session):
        """Tenants table should have all expected columns."""
        expected_columns = {
            "id",
            "name",
            "slug",
            "subscription_tier",
            "status",
            "created_at",
            "updated_at",
        }
        result = await db_session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'tenants'"
            )
        )
        columns = {row[0] for row in result.fetchall()}
        missing = expected_columns - columns
        assert missing == set(), f"Tenants table missing columns: {missing}"

    @pytest.mark.asyncio
    async def test_agent_actions_table_columns(self, db_session):
        """Agent actions table should have all 14 expected columns."""
        expected_columns = {
            "id",
            "tenant_id",
            "agent_type",
            "action_type",
            "target_asin",
            "target_entity_id",
            "status",
            "proposed_change",
            "reasoning",
            "confidence_score",
            "approved_by",
            "approved_at",
            "executed_at",
            "result",
            "created_at",
        }
        result = await db_session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'agent_actions'"
            )
        )
        columns = {row[0] for row in result.fetchall()}
        missing = expected_columns - columns
        assert missing == set(), f"Agent actions table missing columns: {missing}"


# ────────────────────────────────────────────────────────────────────
# Extension Tests
# ────────────────────────────────────────────────────────────────────


class TestExtensions:
    """Verify required PostgreSQL extensions are installed."""

    @pytest.mark.asyncio
    async def test_pgvector_installed(self, db_session):
        """The pgvector extension should be installed."""
        result = await db_session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        row = result.fetchone()
        assert row is not None, "pgvector extension should be installed"
