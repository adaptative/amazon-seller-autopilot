# Amazon Seller Autopilot — Master Execution Plan

## Methodology

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  TASK        │───▶│  MOCKUP      │───▶│  TDD: WRITE  │───▶│  DEVELOP     │───▶│  TEST &  │
│  ASSIGNMENT  │    │  (Stitch/    │    │  TESTS FIRST │    │  (v0/Lovable/│    │  MERGE   │
│  (Priority)  │    │  Figma)      │    │  (Unit+Int)  │    │  Cursor)     │    │  (CI/CD) │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘
```

### Workflow Per Task
1. **Assign** — Pick from sprint backlog by priority (P0 first)
2. **Mockup** — Generate UI in Stitch → review in Figma → finalize
3. **TDD: Tests First** — Write unit tests (Vitest) + integration tests (Playwright) BEFORE implementation
4. **Develop** — Generate code (v0/Lovable/Cursor) that makes tests pass
5. **Review & Merge** — PR review → CI passes all tests → merge to main

### Branch Strategy
```
main (protected)
  ├── develop (integration branch)
  │   ├── feature/SP01-T01-tenant-onboarding
  │   ├── feature/SP01-T02-database-rls
  │   └── feature/SP01-T03-api-gateway
  └── release/v0.1.0
```

### Testing Pyramid
```
        ╱╲          E2E Tests (Playwright)
       ╱  ╲         - Full user flows
      ╱────╲        - Cross-agent scenarios
     ╱      ╲       
    ╱ Integr. ╲     Integration Tests (Vitest + Supertest)
   ╱   Tests   ╲    - API endpoint testing
  ╱─────────────╲   - Agent ↔ API communication
 ╱               ╲  - WebSocket event flows
╱   Unit Tests    ╲  Unit Tests (Vitest + React Testing Library)
╱──────────────────╲ - Components, hooks, utils, agent logic
```

### Definition of Done (DoD)
- [ ] All unit tests passing (≥80% coverage)
- [ ] Integration tests passing
- [ ] No TypeScript errors
- [ ] Lighthouse score ≥ 90 (performance)
- [ ] WCAG 2.1 AA accessibility check passing
- [ ] PR reviewed and approved
- [ ] Documentation updated
- [ ] Deployed to staging environment

---

## PHASE 1: FOUNDATION (Sprints 1–8, Months 1–4)

---

### Sprint 1 (Week 1–2): Project Bootstrap & Auth Infrastructure

#### SP01-T01: Project Scaffolding & Monorepo Setup
**Priority:** P0 | **Assignee:** Backend Lead  
**Type:** Backend + DevOps

**Prompt for Cursor/Claude Code:**
```
Create a monorepo for "amazon-seller-autopilot" using Turborepo with the following packages:

1. apps/web — Next.js 14 app with App Router, TypeScript, Tailwind CSS, shadcn/ui
   - Configure next.config.js with strict mode
   - Set up path aliases: @/components, @/lib, @/hooks, @/types, @/api
   - Install and configure: react-query (TanStack Query v5), zustand, axios, zod
   - Set up shadcn/ui with "new-york" style and slate color scheme

2. apps/api — FastAPI application with Python 3.12
   - Project structure: routers/, services/, agents/, integrations/, models/, schemas/, core/
   - Configure SQLAlchemy + Alembic for migrations
   - Set up Pydantic v2 for request/response schemas
   - Configure CORS, rate limiting (slowapi), and structured logging (structlog)

3. packages/shared-types — Shared TypeScript types exported to both apps
4. packages/ui — Shared component library (extracted from shadcn/ui customizations)
5. packages/eslint-config — Shared ESLint + Prettier config

Configure:
- Turborepo pipeline: build, test, lint, typecheck
- Docker Compose for local development: PostgreSQL 16, Redis 7, LocalStack (S3, SQS)
- GitHub Actions CI: lint → typecheck → test → build on every PR
- Pre-commit hooks: lint-staged + husky
- Environment variable management with .env.example files
```

**Unit Tests (Write FIRST):**
```typescript
// apps/web/__tests__/setup.test.ts
describe('Project Setup', () => {
  it('should have Next.js app running on port 3000', async () => {
    const res = await fetch('http://localhost:3000');
    expect(res.status).toBe(200);
  });
  
  it('should have Tailwind CSS configured', () => {
    const config = require('../tailwind.config');
    expect(config.content).toBeDefined();
    expect(config.theme.extend).toBeDefined();
  });

  it('should have shared types importable', () => {
    const { TenantId } = require('@repo/shared-types');
    expect(TenantId).toBeDefined();
  });
});

// apps/api/tests/test_health.py
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "database" in response.json()
    assert "redis" in response.json()

def test_cors_headers(client):
    response = client.options("/health", headers={"Origin": "http://localhost:3000"})
    assert "access-control-allow-origin" in response.headers
```

**Integration Tests (Write FIRST):**
```typescript
// tests/integration/monorepo.test.ts
describe('Monorepo Integration', () => {
  it('should build all packages without errors', async () => {
    const { exitCode } = await exec('turbo build');
    expect(exitCode).toBe(0);
  });

  it('should pass type checking across all packages', async () => {
    const { exitCode } = await exec('turbo typecheck');
    expect(exitCode).toBe(0);
  });

  it('should run all linting without errors', async () => {
    const { exitCode } = await exec('turbo lint');
    expect(exitCode).toBe(0);
  });
});
```

**DoD:** Monorepo builds, all packages link, Docker Compose starts all services, CI pipeline green.

---

#### SP01-T02: Database Schema & Multi-Tenant RLS
**Priority:** P0 | **Assignee:** Backend Lead  
**Type:** Backend

**Prompt for Cursor/Claude Code:**
```
Create the PostgreSQL database schema for a multi-tenant SaaS platform with Row-Level Security.

Core tables:
1. tenants — id (UUID PK), name, slug, created_at, updated_at, subscription_tier (enum: starter/growth/professional/enterprise), status (enum: active/suspended/trial)
2. users — id (UUID PK), tenant_id (FK→tenants), email (unique per tenant), name, role (enum: owner/admin/manager/viewer), password_hash, mfa_enabled, last_login_at, created_at
3. amazon_connections — id (UUID PK), tenant_id (FK), marketplace_id, seller_id, refresh_token_encrypted, ads_refresh_token_encrypted, connection_status (enum: active/expired/revoked), last_sync_at, created_at
4. agent_actions — id (UUID PK), tenant_id (FK), agent_type (enum: listing/inventory/advertising/pricing/analytics/compliance/orchestrator), action_type, target_asin, target_entity_id, status (enum: proposed/approved/rejected/executing/completed/failed), proposed_change (JSONB), reasoning (TEXT), confidence_score (FLOAT), approved_by (FK→users NULL), approved_at, executed_at, result (JSONB), created_at
5. approval_queue — id (UUID PK), tenant_id (FK), agent_action_id (FK), priority (enum: critical/high/medium/low), auto_approve_eligible (BOOL), expires_at, created_at
6. notification_log — id (UUID PK), tenant_id (FK), type, title, body, severity (enum: critical/warning/info/success), read (BOOL), created_at

Implement:
- RLS policies on ALL tables: CREATE POLICY tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant')::uuid)
- A set_tenant_context() function that sets app.current_tenant
- Alembic migration with upgrade/downgrade
- Indexes on: tenant_id (all tables), email+tenant_id (users), status+tenant_id (agent_actions), created_at (all tables)
- pgvector extension for future semantic search
- Audit trigger that logs all INSERT/UPDATE/DELETE to an audit_log table

Use SQLAlchemy 2.0 mapped classes with proper type hints.
```

**Unit Tests (Write FIRST):**
```python
# apps/api/tests/test_database.py
import pytest
from sqlalchemy import text

class TestMultiTenantRLS:
    def test_tenant_isolation_blocks_cross_tenant_read(self, db_session, tenant_a, tenant_b):
        """Tenant A cannot read Tenant B's data"""
        db_session.execute(text(f"SET app.current_tenant = '{tenant_a.id}'"))
        users = db_session.query(User).all()
        tenant_ids = {u.tenant_id for u in users}
        assert tenant_b.id not in tenant_ids

    def test_tenant_isolation_blocks_cross_tenant_write(self, db_session, tenant_a, tenant_b):
        """Tenant A cannot insert data with Tenant B's tenant_id"""
        db_session.execute(text(f"SET app.current_tenant = '{tenant_a.id}'"))
        with pytest.raises(Exception):
            db_session.add(User(tenant_id=tenant_b.id, email="hack@evil.com"))
            db_session.commit()

    def test_rls_applies_to_all_tables(self, db_session):
        """Every table with tenant_id has an RLS policy"""
        result = db_session.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename != 'alembic_version'
        """))
        for row in result:
            policies = db_session.execute(text(f"""
                SELECT polname FROM pg_policy 
                WHERE polrelid = '{row[0]}'::regclass
            """))
            assert policies.fetchone() is not None, f"Table {row[0]} missing RLS policy"

    def test_audit_log_captures_changes(self, db_session, tenant_a):
        """All data changes are logged to audit_log"""
        db_session.execute(text(f"SET app.current_tenant = '{tenant_a.id}'"))
        user = User(tenant_id=tenant_a.id, email="test@test.com", name="Test")
        db_session.add(user)
        db_session.commit()
        audit = db_session.execute(text(
            "SELECT * FROM audit_log WHERE table_name = 'users' ORDER BY created_at DESC LIMIT 1"
        )).fetchone()
        assert audit is not None
        assert audit.operation == 'INSERT'

    def test_migration_upgrade_downgrade(self, alembic_runner):
        """Migrations can be applied and rolled back cleanly"""
        alembic_runner.migrate_up_to("head")
        alembic_runner.migrate_down_to("base")
        alembic_runner.migrate_up_to("head")  # Should succeed again
```

**DoD:** All RLS tests pass, migrations run clean, audit logging verified, zero cross-tenant leakage.

---

#### SP01-T03: Authentication — Cognito + LWA OAuth
**Priority:** P0 | **Assignee:** Backend Lead + Frontend Dev  
**Type:** Full-stack

**Mockup Prompt (Stitch):**
```
Design a login and signup page for an AI-powered Amazon seller dashboard called "Seller Autopilot."

Login page:
- Clean centered card layout on subtle gradient background
- Logo at top, "Welcome back" heading
- Email and password fields with floating labels
- "Remember me" checkbox and "Forgot password?" link
- Primary "Sign In" button, full width
- Divider with "or continue with"
- Google SSO button and Apple SSO button
- "Don't have an account? Sign up" link at bottom

Signup page:
- Same card layout
- Fields: Full name, Work email, Password (with strength indicator bar), Company name
- Checkbox: "I agree to Terms of Service and Privacy Policy"
- Primary "Create Account" button
- "Already have an account? Sign in" link

Style: Professional SaaS, dark navy (#1B3A5C) accents, clean white cards, Inter font.
Mobile responsive. WCAG AA compliant contrast.
```

**Frontend Prompt (v0):**
```
Create a Next.js authentication page set using shadcn/ui with these specs:

1. LoginPage component:
- Card centered on page with max-w-md
- Form with email input (type="email"), password input (type="password")
- "Remember me" Checkbox component
- "Forgot password?" link
- Full-width Button "Sign In" with loading spinner state
- Separator with "or continue with" text
- Two outline buttons: Google icon + "Google", Apple icon + "Apple"
- Link to signup page
- Form validation with zod: email required + valid format, password required + min 8 chars
- Error alert component for failed login attempts
- Use react-hook-form with zodResolver

2. SignupPage component:
- Same card layout
- Fields: name (required), email (required, valid), password (required, min 8, must contain number + uppercase), company name (required)
- Password strength indicator (weak/medium/strong) with color bar
- Terms checkbox (required)
- Full-width "Create Account" button
- Form validation with zod schema

3. ForgotPasswordPage component:
- Email input + "Send Reset Link" button
- Success state: "Check your email" message

All components must use the "use client" directive, export default, and follow shadcn/ui patterns.
TypeScript with proper types. Tailwind responsive (mobile-first).
```

**Unit Tests (Write FIRST):**
```typescript
// apps/web/__tests__/components/auth/LoginForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '@/components/auth/LoginForm';

describe('LoginForm', () => {
  it('renders email and password fields', () => {
    render(<LoginForm onSubmit={jest.fn()} />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('shows validation error for empty email', async () => {
    render(<LoginForm onSubmit={jest.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid email format', async () => {
    render(<LoginForm onSubmit={jest.fn()} />);
    await userEvent.type(screen.getByLabelText(/email/i), 'notanemail');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/valid email/i)).toBeInTheDocument();
    });
  });

  it('shows validation error for short password', async () => {
    render(<LoginForm onSubmit={jest.fn()} />);
    await userEvent.type(screen.getByLabelText(/email/i), 'test@test.com');
    await userEvent.type(screen.getByLabelText(/password/i), '123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it('calls onSubmit with valid credentials', async () => {
    const onSubmit = jest.fn();
    render(<LoginForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/email/i), 'test@test.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        email: 'test@test.com',
        password: 'Password123',
        rememberMe: false,
      });
    });
  });

  it('shows loading state during submission', async () => {
    render(<LoginForm onSubmit={() => new Promise(() => {})} />);
    await userEvent.type(screen.getByLabelText(/email/i), 'test@test.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
  });

  it('displays server error message', async () => {
    render(<LoginForm onSubmit={jest.fn()} serverError="Invalid credentials" />);
    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
  });
});

// apps/web/__tests__/components/auth/SignupForm.test.tsx
describe('SignupForm', () => {
  it('shows password strength indicator', async () => {
    render(<SignupForm onSubmit={jest.fn()} />);
    const passwordInput = screen.getByLabelText(/password/i);
    
    await userEvent.type(passwordInput, 'abc');
    expect(screen.getByTestId('strength-bar')).toHaveClass('bg-red-500');
    
    await userEvent.clear(passwordInput);
    await userEvent.type(passwordInput, 'Abcdef1!');
    expect(screen.getByTestId('strength-bar')).toHaveClass('bg-green-500');
  });

  it('requires terms acceptance', async () => {
    render(<SignupForm onSubmit={jest.fn()} />);
    // Fill all fields but don't check terms
    await userEvent.type(screen.getByLabelText(/name/i), 'Test User');
    await userEvent.type(screen.getByLabelText(/email/i), 'test@test.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
    await userEvent.type(screen.getByLabelText(/company/i), 'TestCo');
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/must accept terms/i)).toBeInTheDocument();
    });
  });
});
```

**Backend Tests (Write FIRST):**
```python
# apps/api/tests/test_auth.py
import pytest

class TestAuthEndpoints:
    def test_signup_creates_tenant_and_user(self, client):
        response = client.post("/api/v1/auth/signup", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "company_name": "TestCo"
        })
        assert response.status_code == 201
        data = response.json()
        assert "tenant_id" in data
        assert "user_id" in data
        assert "access_token" in data
        assert data["email"] == "test@example.com"

    def test_signup_rejects_duplicate_email(self, client, existing_user):
        response = client.post("/api/v1/auth/signup", json={
            "name": "Duplicate",
            "email": existing_user.email,
            "password": "SecurePass123!",
            "company_name": "DupeCo"
        })
        assert response.status_code == 409

    def test_login_returns_jwt_tokens(self, client, existing_user):
        response = client.post("/api/v1/auth/login", json={
            "email": existing_user.email,
            "password": "SecurePass123!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["tenant_id"] == str(existing_user.tenant_id)

    def test_login_rejects_wrong_password(self, client, existing_user):
        response = client.post("/api/v1/auth/login", json={
            "email": existing_user.email,
            "password": "WrongPassword"
        })
        assert response.status_code == 401

    def test_protected_endpoint_requires_auth(self, client):
        response = client.get("/api/v1/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client, auth_headers):
        response = client.get("/api/v1/me", headers=auth_headers)
        assert response.status_code == 200

    def test_token_refresh(self, client, refresh_token):
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_tenant_context_set_from_jwt(self, client, auth_headers, db_session):
        """JWT token automatically sets tenant context for RLS"""
        response = client.get("/api/v1/me", headers=auth_headers)
        assert response.status_code == 200
        # Verify RLS context was set
        assert response.json()["tenant_id"] is not None
```

**Integration Tests:**
```typescript
// tests/e2e/auth.spec.ts (Playwright)
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('complete signup → login → dashboard flow', async ({ page }) => {
    // 1. Navigate to signup
    await page.goto('/signup');
    
    // 2. Fill signup form
    await page.fill('[name="name"]', 'Test Seller');
    await page.fill('[name="email"]', `test-${Date.now()}@example.com`);
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.fill('[name="companyName"]', 'Test Store');
    await page.check('[name="terms"]');
    await page.click('button[type="submit"]');
    
    // 3. Should redirect to onboarding
    await expect(page).toHaveURL(/\/onboarding/);
    
    // 4. Logout and login again
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.click('button[type="submit"]');
    
    // 5. Should reach dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
  });

  test('unauthorized access redirects to login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});
```

**DoD:** Auth flow works end-to-end, JWT tokens issued, RLS context set automatically, all tests green.

---

### Sprint 2 (Week 3–4): API Gateway, Event Bus & Design System

#### SP02-T01: API Gateway Middleware with Tenant Context
**Priority:** P0 | **Assignee:** Backend Lead  
**Type:** Backend

**Prompt for Cursor/Claude Code:**
```
Build FastAPI middleware stack for the multi-tenant API gateway:

1. TenantContextMiddleware:
   - Extract tenant_id from JWT claims
   - Set PostgreSQL session variable: SET app.current_tenant = '{tenant_id}'
   - Inject tenant_id into request.state.tenant_id for use in route handlers
   - Log tenant_id with every request for debugging

2. RateLimitMiddleware:
   - Per-tenant rate limiting using Redis
   - Limits configurable by subscription tier:
     - Starter: 100 req/min
     - Growth: 500 req/min
     - Professional: 2000 req/min
     - Enterprise: 10000 req/min
   - Return 429 with Retry-After header when exceeded
   - Track usage metrics per tenant per endpoint

3. RequestLoggingMiddleware:
   - Log: method, path, tenant_id, user_id, response_status, latency_ms
   - Use structlog for structured JSON logging
   - Exclude sensitive headers from logs

4. ErrorHandlerMiddleware:
   - Catch all unhandled exceptions
   - Return standardized error response: {"error": {"code": "...", "message": "...", "request_id": "..."}}
   - Never expose stack traces in production
   - Log full error details server-side

5. CORSMiddleware:
   - Allow origins: localhost:3000 (dev), app.sellerautopilot.com (prod)
   - Allow credentials, standard headers + X-Tenant-ID

Create a dependency injection function get_current_tenant() that extracts tenant from request state and can be used in any route handler.
```

**Unit Tests (Write FIRST):**
```python
# apps/api/tests/test_middleware.py
class TestTenantContextMiddleware:
    def test_sets_tenant_from_jwt(self, client, auth_headers_tenant_a):
        response = client.get("/api/v1/me", headers=auth_headers_tenant_a)
        assert response.status_code == 200
        assert response.json()["tenant_id"] == str(TENANT_A_ID)

    def test_rejects_request_without_token(self, client):
        response = client.get("/api/v1/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

    def test_rejects_expired_token(self, client, expired_auth_headers):
        response = client.get("/api/v1/me", headers=expired_auth_headers)
        assert response.status_code == 401

class TestRateLimitMiddleware:
    def test_allows_requests_within_limit(self, client, auth_headers):
        for _ in range(10):
            response = client.get("/api/v1/me", headers=auth_headers)
            assert response.status_code == 200

    def test_blocks_requests_exceeding_limit(self, client, auth_headers, redis_mock):
        # Simulate hitting rate limit
        redis_mock.set_counter(TENANT_A_ID, 101)  # Starter limit = 100
        response = client.get("/api/v1/me", headers=auth_headers)
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_rate_limits_are_per_tenant(self, client, headers_a, headers_b):
        """Tenant A hitting limit doesn't affect Tenant B"""
        # Exhaust tenant A's limit
        for _ in range(101):
            client.get("/api/v1/me", headers=headers_a)
        # Tenant B should still work
        response = client.get("/api/v1/me", headers=headers_b)
        assert response.status_code == 200

class TestErrorHandler:
    def test_returns_standardized_error(self, client, auth_headers):
        response = client.get("/api/v1/nonexistent", headers=auth_headers)
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "request_id" in data["error"]

    def test_no_stack_trace_in_production(self, client, auth_headers):
        response = client.get("/api/v1/trigger-error", headers=auth_headers)
        assert "traceback" not in response.text.lower()
```

**DoD:** All middleware tested, rate limiting per-tenant verified, structured logging confirmed.

---

#### SP02-T02: Design Token System & Core Components
**Priority:** P0 | **Assignee:** Frontend Lead  
**Type:** Frontend

**Mockup Prompt (Stitch):**
```
Generate a design system reference sheet for a SaaS dashboard called "Seller Autopilot."

Show a single page with:
- Color palette: Primary navy (#1B3A5C), Secondary blue (#4A90D9), and semantic colors (success green, warning amber, danger red, info blue). Show 6 shades per color (50, 100, 200, 400, 600, 800).
- Agent-specific accent colors: Listing (blue), Inventory (green), Advertising (orange), Pricing (purple), Analytics (teal), Compliance (gray).
- Typography scale: Display (36px), H1 (30px), H2 (24px), H3 (20px), Body (16px), Small (14px), Caption (12px). Font: Inter.
- Button variants: primary, secondary, outline, ghost, danger, in all sizes (sm, md, lg). Show default, hover, disabled, loading states.
- Form inputs: text, select, checkbox, toggle, radio — showing default, focus, error, disabled states.
- Badge/tag components in all semantic colors.
- Card component with header, body, footer sections.
- Stat card: number, label, trend arrow, sparkline.

Style: Clean, professional, suitable for data-heavy dashboards. Light and dark mode variants.
```

**Frontend Prompt (v0):**
```
Create a comprehensive design system for a SaaS dashboard using shadcn/ui, Tailwind CSS, and TypeScript.

Generate these files:

1. tailwind.config.ts — Extended theme with:
   - Custom colors: primary (navy), secondary (blue), agent colors (listing-blue, inventory-green, advertising-orange, pricing-purple, analytics-teal, compliance-gray)
   - Font family: Inter variable
   - Custom spacing scale (8px grid)
   - Animation classes for: pulse, fade-in, slide-up

2. StatCard component:
   - Props: { title: string, value: string | number, trend: { value: number, direction: 'up' | 'down' }, icon?: LucideIcon, loading?: boolean }
   - Shows: icon, title (muted), value (large bold), trend arrow with percentage, colored green (up) or red (down)
   - Loading state: skeleton shimmer
   - Responsive: full-width on mobile, fixed-width in grid

3. AgentStatusBadge component:
   - Props: { agent: AgentType, status: 'active' | 'idle' | 'error' | 'awaiting_approval' | 'disabled' }
   - Shows agent icon + name + status dot (green/gray/red/yellow/slate)
   - Pulse animation when active
   - Tooltip on hover with last action timestamp

4. ApprovalCard component:
   - Props: { action: AgentAction, onApprove: () => void, onReject: () => void }
   - Shows: agent icon, action description, affected ASINs, estimated impact, confidence score
   - Approve (green) and Reject (red) buttons
   - Expandable reasoning section
   - Priority indicator (colored left border)

5. DataTable component (generic):
   - Props: { columns: ColumnDef[], data: T[], searchable?: boolean, filterable?: boolean, selectable?: boolean, pagination?: boolean }
   - Sortable column headers with arrows
   - Search input with debounce
   - Filter dropdown per column
   - Row selection with bulk actions bar
   - Pagination with page size selector
   - Empty state component
   - Loading skeleton rows
   - Use @tanstack/react-table

All components: TypeScript, forwardRef, keyboard accessible, Storybook-ready.
```

**Unit Tests (Write FIRST):**
```typescript
// packages/ui/__tests__/StatCard.test.tsx
describe('StatCard', () => {
  it('renders value and title', () => {
    render(<StatCard title="Revenue" value="$12,450" trend={{ value: 12.5, direction: 'up' }} />);
    expect(screen.getByText('$12,450')).toBeInTheDocument();
    expect(screen.getByText('Revenue')).toBeInTheDocument();
  });

  it('shows green arrow for upward trend', () => {
    render(<StatCard title="Revenue" value="$12,450" trend={{ value: 12.5, direction: 'up' }} />);
    const trend = screen.getByTestId('trend-indicator');
    expect(trend).toHaveClass('text-green');
    expect(screen.getByText('+12.5%')).toBeInTheDocument();
  });

  it('shows red arrow for downward trend', () => {
    render(<StatCard title="ACoS" value="28.5%" trend={{ value: 3.2, direction: 'down' }} />);
    const trend = screen.getByTestId('trend-indicator');
    expect(trend).toHaveClass('text-red');
  });

  it('renders skeleton when loading', () => {
    render(<StatCard title="Revenue" value="" loading={true} trend={{ value: 0, direction: 'up' }} />);
    expect(screen.getByTestId('stat-skeleton')).toBeInTheDocument();
  });
});

// packages/ui/__tests__/ApprovalCard.test.tsx
describe('ApprovalCard', () => {
  const mockAction = {
    id: '1', agentType: 'pricing', description: 'Reduce price on ASIN B08XYZ to $24.99',
    affectedAsins: ['B08XYZ'], estimatedImpact: '+15% Buy Box win rate',
    confidence: 0.87, reasoning: 'Competitor dropped price by 8%...',
    priority: 'high' as const,
  };

  it('renders action description and agent type', () => {
    render(<ApprovalCard action={mockAction} onApprove={jest.fn()} onReject={jest.fn()} />);
    expect(screen.getByText(/Reduce price/)).toBeInTheDocument();
    expect(screen.getByText(/pricing/i)).toBeInTheDocument();
  });

  it('calls onApprove when approve button clicked', async () => {
    const onApprove = jest.fn();
    render(<ApprovalCard action={mockAction} onApprove={onApprove} onReject={jest.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /approve/i }));
    expect(onApprove).toHaveBeenCalledWith(mockAction.id);
  });

  it('shows confidence score as percentage', () => {
    render(<ApprovalCard action={mockAction} onApprove={jest.fn()} onReject={jest.fn()} />);
    expect(screen.getByText('87%')).toBeInTheDocument();
  });

  it('expands reasoning section on click', async () => {
    render(<ApprovalCard action={mockAction} onApprove={jest.fn()} onReject={jest.fn()} />);
    expect(screen.queryByText(/Competitor dropped/)).not.toBeVisible();
    await userEvent.click(screen.getByText(/show reasoning/i));
    expect(screen.getByText(/Competitor dropped/)).toBeVisible();
  });

  it('shows priority indicator color', () => {
    render(<ApprovalCard action={mockAction} onApprove={jest.fn()} onReject={jest.fn()} />);
    expect(screen.getByTestId('priority-border')).toHaveClass('border-l-orange');
  });
});

// packages/ui/__tests__/DataTable.test.tsx
describe('DataTable', () => {
  const columns = [
    { accessorKey: 'name', header: 'Name' },
    { accessorKey: 'price', header: 'Price' },
    { accessorKey: 'status', header: 'Status' },
  ];
  const data = [
    { name: 'Widget A', price: 29.99, status: 'active' },
    { name: 'Widget B', price: 19.99, status: 'inactive' },
    { name: 'Widget C', price: 39.99, status: 'active' },
  ];

  it('renders all rows', () => {
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getAllByRole('row')).toHaveLength(4); // header + 3 data
  });

  it('sorts by column when header clicked', async () => {
    render(<DataTable columns={columns} data={data} />);
    await userEvent.click(screen.getByText('Price'));
    const rows = screen.getAllByRole('row');
    expect(rows[1]).toHaveTextContent('19.99'); // Ascending: lowest first
  });

  it('filters data with search input', async () => {
    render(<DataTable columns={columns} data={data} searchable />);
    await userEvent.type(screen.getByPlaceholderText(/search/i), 'Widget A');
    await waitFor(() => {
      expect(screen.getAllByRole('row')).toHaveLength(2); // header + 1 match
    });
  });

  it('shows empty state when no data', () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    render(<DataTable columns={columns} data={[]} loading />);
    expect(screen.getAllByTestId('skeleton-row')).toHaveLength(5);
  });
});
```

**DoD:** All components render, pass unit tests, accessible, work in light/dark mode.

---

### Sprint 3 (Week 5–6): Amazon OAuth & SP-API Connector

#### SP03-T01: Amazon SP-API Connector Service
**Priority:** P0 | **Assignee:** Backend Lead  
**Type:** Backend Integration

**Prompt for Cursor/Claude Code:**
```
Build a reusable Amazon SP-API connector service in Python:

File: apps/api/integrations/sp_api/connector.py

class SPAPIConnector:
    """Centralized SP-API client with LWA token management, rate limiting, and caching."""

    Features:
    1. Token Management:
       - Store encrypted refresh tokens per tenant+marketplace
       - Auto-refresh access tokens before expiry (5-min buffer)
       - Thread-safe token refresh with locking

    2. Rate Limit Management:
       - Per-tenant, per-endpoint rate tracking in Redis
       - Adaptive throttling: slow down BEFORE hitting limits
       - Priority queue: user-initiated (high) > agent-initiated (normal) > background (low)
       - Respect SP-API's rate limit response headers

    3. Request Caching:
       - Cache stable data (catalog info): 4 hours
       - Cache semi-stable data (listings): 30 minutes
       - Cache volatile data (prices, inventory): 5 minutes
       - Cache key includes: tenant_id + endpoint + params hash

    4. Error Handling:
       - Classify: retryable (429, 500, 503) vs non-retryable (400, 403, 404)
       - Exponential backoff with jitter for retryable errors
       - Max 3 retries per request
       - Circuit breaker: if >50% of calls fail in 60s window, pause for 30s

    5. Logging:
       - Log every API call: tenant_id, endpoint, response_time, status, cached
       - Metrics for billing: count API calls per tenant per day

    Implement methods for:
    - get_listings(tenant_id, marketplace_id, sku=None)
    - get_pricing(tenant_id, marketplace_id, asins: list)
    - get_inventory(tenant_id, marketplace_id)
    - get_orders(tenant_id, marketplace_id, created_after=None)
    - submit_feed(tenant_id, marketplace_id, feed_type, content)
    - subscribe_notification(tenant_id, notification_type, destination_arn)

    Each method should use the appropriate SP-API endpoint and handle pagination automatically.
```

**Unit Tests (Write FIRST):**
```python
# apps/api/tests/integrations/test_sp_api_connector.py
import pytest
from unittest.mock import AsyncMock, patch
from integrations.sp_api.connector import SPAPIConnector

class TestSPAPIConnector:
    @pytest.fixture
    def connector(self, redis_mock, db_session):
        return SPAPIConnector(redis=redis_mock, db=db_session)

    def test_auto_refreshes_expired_token(self, connector, mock_lwa_server):
        """Should refresh access token when it's expired"""
        mock_lwa_server.set_token_expiry(-60)  # Expired 60s ago
        connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")
        assert mock_lwa_server.refresh_called is True

    def test_caches_stable_data(self, connector, redis_mock):
        """Catalog data should be cached for 4 hours"""
        connector.get_catalog_item(TENANT_A_ID, "ATVPDKIKX0DER", "B08XYZ")
        connector.get_catalog_item(TENANT_A_ID, "ATVPDKIKX0DER", "B08XYZ")
        assert connector.api_call_count == 1  # Second call from cache

    def test_doesnt_cache_volatile_data_long(self, connector, redis_mock):
        """Price data cache should expire in 5 minutes"""
        connector.get_pricing(TENANT_A_ID, "ATVPDKIKX0DER", ["B08XYZ"])
        cached = redis_mock.get_ttl(f"sp_api:{TENANT_A_ID}:pricing:B08XYZ")
        assert cached <= 300  # 5 minutes

    def test_rate_limit_adaptive_throttle(self, connector, redis_mock):
        """Should slow down before hitting rate limit"""
        redis_mock.set_counter(f"ratelimit:{TENANT_A_ID}:listings", 25)  # Near limit of 30/sec
        start = time.time()
        connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")
        elapsed = time.time() - start
        assert elapsed > 0.1  # Should have added delay

    def test_retries_on_429(self, connector, mock_sp_api):
        """Should retry with backoff on 429 Too Many Requests"""
        mock_sp_api.set_responses([429, 429, 200])
        result = connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")
        assert result is not None
        assert mock_sp_api.call_count == 3

    def test_no_retry_on_400(self, connector, mock_sp_api):
        """Should NOT retry on 400 Bad Request"""
        mock_sp_api.set_responses([400])
        with pytest.raises(SPAPIClientError):
            connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")
        assert mock_sp_api.call_count == 1

    def test_circuit_breaker_opens_on_failures(self, connector, mock_sp_api):
        """Should stop calling API after >50% failure rate"""
        mock_sp_api.set_responses([500] * 10)
        for _ in range(10):
            try:
                connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")
            except:
                pass
        with pytest.raises(CircuitBreakerOpenError):
            connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")

    def test_tenant_isolation_in_api_calls(self, connector):
        """Each tenant's API calls use their own credentials"""
        connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")
        connector.get_listings(TENANT_B_ID, "ATVPDKIKX0DER")
        assert connector.get_used_credentials(0).tenant_id == TENANT_A_ID
        assert connector.get_used_credentials(1).tenant_id == TENANT_B_ID

    def test_handles_pagination_automatically(self, connector, mock_sp_api):
        """Should follow nextToken pagination until all results retrieved"""
        mock_sp_api.set_paginated_response(total_items=150, page_size=50)
        result = connector.get_inventory(TENANT_A_ID, "ATVPDKIKX0DER")
        assert len(result) == 150
        assert mock_sp_api.call_count == 3  # 3 pages

    def test_logs_api_calls_for_billing(self, connector, db_session):
        """Every API call should be logged for usage-based billing"""
        connector.get_listings(TENANT_A_ID, "ATVPDKIKX0DER")
        logs = db_session.query(APICallLog).filter_by(tenant_id=TENANT_A_ID).all()
        assert len(logs) == 1
        assert logs[0].endpoint == "listings"
        assert logs[0].response_time_ms > 0
```

**DoD:** Connector handles auth, rate limiting, caching, retries, circuit breaker. All tests green.

---

### Sprint 4 (Week 7–8): Listing Agent v1 + Pricing Agent v1

> _Sprints 4–8 continue the same pattern. Each task includes:_
> 1. _Stitch mockup prompt for the UI_
> 2. _v0/Lovable prompt for component generation_
> 3. _Backend prompt for agent logic_
> 4. _Unit tests written BEFORE implementation_
> 5. _Integration tests for cross-system verification_

#### SP04-T01: Listing Agent — AI Content Generation
**Priority:** P0 | **Assignee:** AI/Agent Developer  
**Type:** Backend Agent

**Prompt for Cursor/Claude Code:**
```
Build the Listing Agent for Amazon product listing generation:

File: apps/api/agents/listing_agent.py

class ListingAgent:
    """AI agent that generates and optimizes Amazon product listings."""

    def __init__(self, llm_client, sp_api_connector, tenant_id):
        self.llm = llm_client  # Claude API
        self.sp_api = sp_api_connector
        self.tenant_id = tenant_id

    async def generate_listing(self, input: ListingGenerationInput) -> ProposedListing:
        """
        Input: product_name, key_features (list), target_keywords (list), 
               category, brand_voice (professional/casual/technical), competitor_asins (optional)
        
        Steps:
        1. Fetch product type definition from SP-API for the category
        2. If competitor_asins provided, fetch their listings from Catalog Items API
        3. Analyze top competitor content for keyword patterns and structure
        4. Generate optimized content using Claude:
           - Title: ≤200 chars, front-loaded with primary keywords, brand name first
           - Bullet points: 5 bullets, each starting with CAPS benefit, keyword-rich
           - Description: 2000 chars max, storytelling format, keyword-integrated
           - Search terms: 250 bytes, no duplicates of title/bullets words
        5. Validate against product type schema (required attributes)
        6. Calculate SEO score (keyword density, coverage, readability)
        7. Return ProposedListing with content + SEO score + reasoning

        The listing MUST be proposed (status='proposed') and await human approval
        before being submitted to Amazon via Listings Items API.
        """
        pass

    async def analyze_listing_quality(self, asin: str) -> ListingQualityReport:
        """Fetch current listing, analyze quality, and generate improvement suggestions."""
        pass

    async def handle_listing_issue(self, notification: ListingIssueNotification) -> AgentAction:
        """React to LISTINGS_ITEM_ISSUES_CHANGE notification."""
        pass
```

**Unit Tests (Write FIRST):**
```python
# apps/api/tests/agents/test_listing_agent.py
class TestListingAgent:
    @pytest.fixture
    def agent(self, mock_llm, mock_sp_api, tenant_a):
        return ListingAgent(llm_client=mock_llm, sp_api=mock_sp_api, tenant_id=tenant_a.id)

    async def test_generates_title_under_200_chars(self, agent):
        result = await agent.generate_listing(ListingGenerationInput(
            product_name="Wireless Bluetooth Earbuds",
            key_features=["Active Noise Cancelling", "40h Battery", "IPX5 Waterproof"],
            target_keywords=["wireless earbuds", "noise cancelling", "bluetooth"],
            category="HEADPHONES",
            brand_voice="professional"
        ))
        assert len(result.title) <= 200

    async def test_generates_exactly_5_bullet_points(self, agent):
        result = await agent.generate_listing(SAMPLE_INPUT)
        assert len(result.bullet_points) == 5

    async def test_bullet_points_start_with_caps_benefit(self, agent):
        result = await agent.generate_listing(SAMPLE_INPUT)
        for bullet in result.bullet_points:
            first_word = bullet.split()[0]
            assert first_word == first_word.upper(), f"Bullet should start with CAPS: {bullet}"

    async def test_search_terms_under_250_bytes(self, agent):
        result = await agent.generate_listing(SAMPLE_INPUT)
        assert len(result.search_terms.encode('utf-8')) <= 250

    async def test_search_terms_no_title_duplicates(self, agent):
        result = await agent.generate_listing(SAMPLE_INPUT)
        title_words = set(result.title.lower().split())
        search_words = set(result.search_terms.lower().split())
        overlap = title_words & search_words
        assert len(overlap) == 0, f"Search terms duplicate title words: {overlap}"

    async def test_includes_target_keywords_in_content(self, agent):
        result = await agent.generate_listing(SAMPLE_INPUT)
        full_text = f"{result.title} {' '.join(result.bullet_points)} {result.description}".lower()
        for keyword in SAMPLE_INPUT.target_keywords:
            assert keyword.lower() in full_text, f"Missing keyword: {keyword}"

    async def test_returns_seo_score(self, agent):
        result = await agent.generate_listing(SAMPLE_INPUT)
        assert 0 <= result.seo_score <= 100
        assert result.seo_breakdown is not None

    async def test_validates_against_product_type_schema(self, agent, mock_sp_api):
        mock_sp_api.set_product_type_definition("HEADPHONES", required_attrs=["brand", "color"])
        result = await agent.generate_listing(SAMPLE_INPUT)
        assert "brand" in result.attributes
        assert "color" in result.attributes

    async def test_proposed_listing_requires_approval(self, agent):
        result = await agent.generate_listing(SAMPLE_INPUT)
        assert result.status == "proposed"
        assert result.submitted_to_amazon is False

    async def test_analyzes_competitor_listings_when_provided(self, agent, mock_sp_api):
        mock_sp_api.set_catalog_items(["B08COMP1", "B08COMP2"], {...})
        result = await agent.generate_listing(ListingGenerationInput(
            **SAMPLE_INPUT.__dict__,
            competitor_asins=["B08COMP1", "B08COMP2"]
        ))
        assert result.competitor_analysis is not None
        assert len(result.competitor_analysis.analyzed_asins) == 2

    async def test_respects_brand_voice_setting(self, agent):
        casual = await agent.generate_listing(ListingGenerationInput(**{**SAMPLE_INPUT.__dict__, "brand_voice": "casual"}))
        professional = await agent.generate_listing(ListingGenerationInput(**{**SAMPLE_INPUT.__dict__, "brand_voice": "professional"}))
        # Casual should use more informal language
        assert casual.title != professional.title
```

**DoD:** Agent generates valid listings, respects all Amazon constraints, proposed changes saved for approval, all tests green.

---

## PHASE 2–4: SPRINT MAP (Summary)

> _Each sprint below follows the identical structure shown above._
> _Full prompts for every task are in the sprint detail files._

### Phase 2: Core Agents (Sprints 5–12)

| Sprint | Weeks | Focus | Key Deliverables |
|--------|-------|-------|-----------------|
| **5** | 9–10 | Advertising Agent + MCP | MCP Server connection, campaign creation via prompts, campaign table UI |
| **6** | 11–12 | Bid Optimization + Keywords | Auto-bid adjustment, keyword harvesting, search term reports, dayparting |
| **7** | 13–14 | Inventory Agent v1 | Real-time monitoring, FBA/AWD tracking, low-stock alerts, inventory dashboard |
| **8** | 15–16 | Demand Forecasting | ML forecast model, replenishment planner, forecast charts, cross-agent LOW_STOCK event |
| **9** | 17–18 | Analytics Agent + Financials | Data Kiosk integration, SKU profitability, P&L dashboard, TACoS tracking |
| **10** | 19–20 | Orchestrator Agent | Cross-agent coordination, conflict resolution, approval queue management |
| **11** | 21–22 | Competitor Analysis | ASIN tracking, Brand Analytics, market share estimates, competitor dashboard |
| **12** | 23–24 | Keyword Research + SEO | Reverse ASIN, keyword gaps, auto-update search terms, keyword performance dashboard |

### Phase 3: Advanced (Sprints 13–18)

| Sprint | Weeks | Focus | Key Deliverables |
|--------|-------|-------|-----------------|
| **13** | 25–26 | A+ Content Agent | Module generation, A+ Content API, visual editor, moderation flow |
| **14** | 27–28 | Brand Store Management | Store API integration, page management, section analytics |
| **15** | 29–30 | Compliance Agent | Account health monitoring, EPR, listing restrictions, compliance dashboard |
| **16** | 31–32 | Promotions Agent | Deal creation, promotional calendar, ROI tracking, promotions UI |
| **17** | 33–34 | Multi-Marketplace | Listing translation, cross-market campaigns, marketplace switcher |
| **18** | 35–36 | Product Launch Orchestration | Multi-agent launch sequence, launch velocity tracking, post-launch analysis |

### Phase 4: Scale (Sprints 19–24)

| Sprint | Weeks | Focus | Key Deliverables |
|--------|-------|-------|-----------------|
| **19** | 37–38 | SD/DSP Advertising | Sponsored Display, Amazon DSP, retargeting campaigns |
| **20** | 39–40 | Enterprise Features | Multi-brand management, agency dashboard, SSO/SAML |
| **21** | 41–42 | Advanced ML Models | Custom demand forecasting, predictive pricing, anomaly detection |
| **22** | 43–44 | Mobile App | React Native shell, approval workflows, push notifications |
| **23** | 45–46 | Marketplace Intelligence | Anonymized cross-tenant benchmarks, category insights |
| **24** | 47–48 | Performance & Polish | Load testing, security audit, documentation, GA launch |

---

## CI/CD Pipeline Spec

```yaml
# .github/workflows/ci.yml (detailed spec)
name: CI/CD Pipeline

on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [main]

jobs:
  lint-and-typecheck:
    # Runs: ESLint, Prettier, TypeScript compiler, Python mypy, ruff
    # Must pass before any other job

  unit-tests:
    needs: lint-and-typecheck
    strategy:
      matrix:
        package: [web, api, ui]
    # Runs: vitest (frontend), pytest (backend)
    # Coverage threshold: 80% minimum
    # Uploads coverage to Codecov

  integration-tests:
    needs: unit-tests
    # Spins up: PostgreSQL, Redis, LocalStack
    # Runs: API integration tests (pytest with TestClient)
    # Runs: Frontend integration tests (Playwright)
    # Tests cross-service communication

  e2e-tests:
    needs: integration-tests
    # Deploys to staging environment
    # Runs: Full Playwright E2E suite
    # Tests complete user flows

  deploy-staging:
    needs: e2e-tests
    if: github.ref == 'refs/heads/develop'
    # Deploys to staging: Vercel (frontend) + ECS (backend)

  deploy-production:
    needs: e2e-tests
    if: github.ref == 'refs/heads/main'
    # Requires manual approval
    # Deploys to production with blue-green strategy
```

---

## Test Coverage Requirements

| Module | Unit Test Min | Integration Min | E2E Flows |
|--------|-------------|-----------------|-----------|
| Auth & Onboarding | 90% | 85% | Signup → Dashboard |
| SP-API Connector | 90% | 80% | OAuth → API Call → Response |
| Listing Agent | 85% | 80% | Generate → Approve → Publish |
| Pricing Agent | 85% | 80% | Price Change → Reprice → Verify |
| Advertising Agent | 85% | 80% | Campaign Create → Optimize → Report |
| Inventory Agent | 85% | 80% | Monitor → Alert → Reorder |
| Orchestrator | 80% | 85% | Cross-Agent Workflow |
| Dashboard UI | 80% | 75% | Navigation + Interactions |
| Approval Flow | 90% | 90% | Propose → Approve → Execute |
