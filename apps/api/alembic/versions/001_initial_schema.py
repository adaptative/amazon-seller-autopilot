"""Initial schema with multi-tenant RLS, audit triggers, and pgvector.

Revision ID: 001
Revises:
Create Date: 2026-04-04

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ──────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"vector\"")

    # ── Tenants ──────���──────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("subscription_tier", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.CheckConstraint(
            "subscription_tier IN ('starter', 'growth', 'professional', 'enterprise')",
            name="ck_tenants_subscription_tier",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'trial', 'cancelled')",
            name="ck_tenants_status",
        ),
    )

    # ── Users ─────��─────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'manager', 'viewer')",
            name="ck_users_role",
        ),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ── Amazon Connections ──────────────────────────────────────
    op.create_table(
        "amazon_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("marketplace_id", sa.String(50), nullable=False),
        sa.Column("seller_id", sa.String(50), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(1024), nullable=True),
        sa.Column("ads_refresh_token_encrypted", sa.String(1024), nullable=True),
        sa.Column("connection_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "connection_status IN ('pending', 'active', 'disconnected', 'error')",
            name="ck_amazon_connections_status",
        ),
    )
    op.create_index("ix_amazon_connections_tenant_id", "amazon_connections", ["tenant_id"])

    # ── Agent Actions ──────────────────────────────────────────��
    op.create_table(
        "agent_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("target_asin", sa.String(20), nullable=True),
        sa.Column("target_entity_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="proposed"),
        sa.Column("proposed_change", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "agent_type IN ('listing', 'inventory', 'advertising', 'pricing', 'analytics', 'compliance', 'orchestrator')",
            name="ck_agent_actions_agent_type",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected', 'executing', 'completed', 'failed')",
            name="ck_agent_actions_status",
        ),
    )
    op.create_index("ix_agent_actions_tenant_id", "agent_actions", ["tenant_id"])
    op.create_index("ix_agent_actions_tenant_status", "agent_actions", ["tenant_id", "status"])
    op.create_index("ix_agent_actions_tenant_created", "agent_actions", ["tenant_id", "created_at"])

    # ── Approval Queue ──────────────────────────────────────────
    op.create_table(
        "approval_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_action_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_actions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.String(50), nullable=False, server_default="medium"),
        sa.Column("auto_approve_eligible", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="ck_approval_queue_priority",
        ),
    )
    op.create_index("ix_approval_queue_tenant_id", "approval_queue", ["tenant_id"])

    # ── Notification Log ────��───────────────────────────────────
    op.create_table(
        "notification_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("severity", sa.String(50), nullable=False, server_default="info"),
        sa.Column("read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "severity IN ('critical', 'warning', 'info', 'success')",
            name="ck_notification_log_severity",
        ),
    )
    op.create_index("ix_notification_log_tenant_id", "notification_log", ["tenant_id"])

    # ── Audit Log (no RLS) ──────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("row_id", sa.String(255), nullable=False),
        sa.Column("old_data", postgresql.JSON, nullable=True),
        sa.Column("new_data", postgresql.JSON, nullable=True),
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])

    # ── Application Role (non-superuser for RLS enforcement) ────
    # Password is set via environment variable APP_USER_PASSWORD, defaulting
    # to 'app_user_pass' for local development only.
    import os
    app_user_password = os.getenv("APP_USER_PASSWORD", "app_user_pass")
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                EXECUTE format(
                    'CREATE ROLE app_user LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE',
                    '{app_user_password}'
                );
            END IF;
        END
        $$;
    """)
    op.execute("GRANT USAGE ON SCHEMA public TO app_user")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user")

    # ── Row-Level Security ──────────────────────────────────────
    rls_tables = [
        "users",
        "amazon_connections",
        "agent_actions",
        "approval_queue",
        "notification_log",
    ]
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_policy ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant')::uuid) "
            f"WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid)"
        )

    # ── Audit Trigger Function ──────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_trigger_func()
        RETURNS TRIGGER AS $$
        DECLARE
            _row_id TEXT;
            _tenant_id UUID;
            _old_data JSONB;
            _new_data JSONB;
        BEGIN
            -- Determine row_id from id column
            IF TG_OP = 'DELETE' THEN
                _row_id := OLD.id::TEXT;
            ELSE
                _row_id := NEW.id::TEXT;
            END IF;

            -- Determine tenant_id (tenants table uses id itself)
            IF TG_TABLE_NAME = 'tenants' THEN
                IF TG_OP = 'DELETE' THEN
                    _tenant_id := OLD.id;
                ELSE
                    _tenant_id := NEW.id;
                END IF;
            ELSE
                IF TG_OP = 'DELETE' THEN
                    _tenant_id := OLD.tenant_id;
                ELSE
                    _tenant_id := NEW.tenant_id;
                END IF;
            END IF;

            -- Build old/new data
            IF TG_OP = 'INSERT' THEN
                _old_data := NULL;
                _new_data := row_to_json(NEW)::JSONB;
            ELSIF TG_OP = 'UPDATE' THEN
                _old_data := row_to_json(OLD)::JSONB;
                _new_data := row_to_json(NEW)::JSONB;
            ELSIF TG_OP = 'DELETE' THEN
                _old_data := row_to_json(OLD)::JSONB;
                _new_data := NULL;
            END IF;

            INSERT INTO audit_log (table_name, operation, tenant_id, row_id, old_data, new_data, changed_by)
            VALUES (TG_TABLE_NAME, TG_OP, _tenant_id, _row_id, _old_data, _new_data, current_user);

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Attach audit triggers to all tables except audit_log and tenants
    # (tenants don't have tenant_id referencing themselves in the same way)
    audit_tables = [
        "tenants",
        "users",
        "amazon_connections",
        "agent_actions",
        "approval_queue",
        "notification_log",
    ]
    for table in audit_tables:
        op.execute(f"""
            CREATE TRIGGER audit_{table}_trigger
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION audit_trigger_func()
        """)


def downgrade() -> None:
    # Drop triggers
    audit_tables = [
        "tenants",
        "users",
        "amazon_connections",
        "agent_actions",
        "approval_queue",
        "notification_log",
    ]
    for table in audit_tables:
        op.execute(f"DROP TRIGGER IF EXISTS audit_{table}_trigger ON {table}")

    op.execute("DROP FUNCTION IF EXISTS audit_trigger_func()")

    # Drop RLS policies
    rls_tables = [
        "users",
        "amazon_connections",
        "agent_actions",
        "approval_queue",
        "notification_log",
    ]
    for table in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop tables in reverse dependency order
    op.drop_table("audit_log")
    op.drop_table("notification_log")
    op.drop_table("approval_queue")
    op.drop_table("agent_actions")
    op.drop_table("amazon_connections")
    op.drop_table("users")
    op.drop_table("tenants")

    # Drop app_user role (must revoke default privileges first)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM app_user';
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_user';
                EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM app_user';
                EXECUTE 'REVOKE USAGE ON SCHEMA public FROM app_user';
                EXECUTE 'DROP ROLE app_user';
            END IF;
        END
        $$;
    """)

    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
