"""commerce, billing, payments, entitlements, usage (Phase 17)

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-05

STRICTLY ADDITIVE — creates EIGHT tables plus the FREE-plan catalog seed;
no existing table, column, index, constraint, or policy is touched.
Rollback drops exactly these tables and the seed rows.

Existing tables were inspected first (Phase 17 §33): jobseeker core is
free and must NOT be gated, so no route/table was changed to enforce
billing. The new commerce domain is configuration-driven: the only plan
seeded is FREE (price 0.00, NUMERIC). Paid plans are catalog rows an
operator adds when pricing is decided — no final prices are invented.

Tables (each organization-scoped; money NUMERIC; provider references
only — no card data, no credentials):

1. commerce_plans            — configurable plan catalog (code, interval,
                               currency, NUMERIC price, published flag).
2. commerce_plan_entitlements — plan -> feature code -> limit (NULL =
                               unlimited). Feature codes are the controlled
                               ENTITLEMENT_CODES set.
3. commerce_subscriptions    — ORGANIZATION-owned lifecycle rows
                               (trial/active/past_due/paused/cancelled/
                               expired); provider subscription reference
                               only; one live sub per org (service-enforced).
4. commerce_invoices         — NUMERIC invoice (subtotal/tax/total) with
                               bounded JSON line items + lifecycle.
5. usage_records             — tenant-scoped usage for countable features.
6. payment_transactions      — provider payment attempt, idempotency key,
                               provider references, NUMERIC amount.
7. payment_refunds           — idempotent authorized refunds (<= paid).
8. payment_webhook_events    — signature-verified provider envelope,
                               unique (provider, event_id), no raw payload.

RLS: designed for the future stage-B/C groups; not enabled in this phase
(see PHASE_13_RLS_MATRIX). Service + API layers enforce tenant isolation.
"""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
tz = sa.DateTime(timezone=True)
money = sa.Numeric(14, 2)

# Deterministic UUIDs for the FREE plan seed.
FREE_PLAN_ID = "10000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "commerce_plans",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("price", money, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("seat_included", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("code", name="uq_commerce_plans_code"),
    )

    op.create_table(
        "commerce_plan_entitlements",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "plan_id",
            uuid_type,
            sa.ForeignKey("commerce_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entitlement_code", sa.String(60), nullable=False),
        sa.Column("limit_value", money),
        sa.Column("unit", sa.String(40)),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("plan_id", "entitlement_code", name="uq_plan_entitlement_feature"),
    )

    op.create_table(
        "commerce_subscriptions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id",
            uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            uuid_type,
            sa.ForeignKey("commerce_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("price_amount", money, nullable=False),
        sa.Column("seat_count", sa.Integer(), nullable=False),
        sa.Column("provider_subscription_id", sa.String(120)),
        sa.Column("trial_ends_at", tz),
        sa.Column("current_period_start", tz),
        sa.Column("current_period_end", tz),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column(
            "created_by_user_id",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("cancelled_at", tz),
        sa.Column("cancel_reason", sa.String(60)),
        sa.Column("note", sa.String(300)),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_subscriptions_org_status", "commerce_subscriptions", ["organization_id", "status"])
    op.create_index("ix_subscriptions_provider_ref", "commerce_subscriptions", ["provider_subscription_id"])

    op.create_table(
        "commerce_invoices",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id",
            uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("invoice_number", sa.String(40), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("subtotal_amount", money, nullable=False),
        sa.Column("tax_amount", money, nullable=False),
        sa.Column("total_amount", money, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("items", sa.JSON()),
        sa.Column("payment_transaction_id", uuid_type),
        sa.Column("issued_at", tz),
        sa.Column("due_at", tz),
        sa.Column("paid_at", tz),
        sa.Column("note", sa.String(300)),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("invoice_number", name="uq_invoice_number"),
    )
    op.create_index("ix_invoices_org_status", "commerce_invoices", ["organization_id", "status"])

    op.create_table(
        "usage_records",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id",
            uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feature", sa.String(60), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reference_type", sa.String(60)),
        sa.Column("reference_id", sa.String(64)),
        sa.Column("recorded_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index(
        "ix_usage_records_org_feature", "usage_records", ["organization_id", "feature", "recorded_at"]
    )

    op.create_table(
        "payment_transactions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id",
            uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_customer_id", sa.String(120)),
        sa.Column("provider_payment_id", sa.String(120)),
        sa.Column("amount", money, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("description", sa.String(240)),
        sa.Column("idempotency_key", sa.String(120)),
        sa.Column("failure_code", sa.String(60)),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("succeeded_at", tz),
        sa.Column("failed_at", tz),
        sa.Column("refunded_amount", money, nullable=False),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_idempotency"),
    )
    op.create_index("ix_payments_org_status", "payment_transactions", ["organization_id", "status"])
    op.create_index("ix_payments_provider_ref", "payment_transactions", ["provider_payment_id"])

    op.create_table(
        "payment_refunds",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "transaction_id",
            uuid_type,
            sa.ForeignKey("payment_transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_refund_id", sa.String(120)),
        sa.Column("amount", money, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(240)),
        sa.Column("idempotency_key", sa.String(120)),
        sa.Column("authorized_by_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("succeeded_at", tz),
        sa.Column("failed_at", tz),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_refund_idempotency"),
    )
    op.create_index("ix_refunds_transaction", "payment_refunds", ["transaction_id"])

    op.create_table(
        "payment_webhook_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("event_id", sa.String(120), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("signature_valid", sa.Boolean()),
        sa.Column("note", sa.String(240)),
        sa.Column("received_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", tz),
        sa.UniqueConstraint("provider", "event_id", name="uq_webhook_event_id"),
    )
    op.create_index("ix_webhook_events_status", "payment_webhook_events", ["status"])

    # --- FREE plan catalog seed (price 0.00; jobseeker core stays free). -------
    op.execute(
        sa.text(
            "INSERT INTO commerce_plans "
            "(id, code, name, description, billing_interval, currency, price, active, "
            "published, seat_included, sort_order, created_at, updated_at) "
            "VALUES (:id, 'free', 'Free', "
            "'Free plan for organizations on the AskTrabaajo platform. "
            "Jobseeker core functionality is always free.', "
            "'month', 'USD', 0.00, true, true, 0, 0, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ).bindparams(id=FREE_PLAN_ID)
    )
    # Free-plan entitlements: unlimited core, zero paid/premium usage.
    FREE_ENTITLEMENTS = [
        ("jobs.create", "5"),
        ("jobs.active", "5"),
        ("candidate.search", "20"),
        ("candidate.outreach", "5"),
        ("ai.athena", "20"),
        ("ai.interview", "0"),
        ("analytics", None),
        ("premium_support", "0"),
    ]
    for i, (code, limit) in enumerate(FREE_ENTITLEMENTS):
        ent_id = f"10000000-0000-4000-8000-{1000 + i:012d}"
        if limit is None:
            op.execute(
                sa.text(
                    "INSERT INTO commerce_plan_entitlements "
                    "(id, plan_id, entitlement_code, limit_value, created_at, updated_at) "
                    "VALUES (:id, :plan_id, :code, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ).bindparams(id=ent_id, plan_id=FREE_PLAN_ID, code=code)
            )
        else:
            op.execute(
                sa.text(
                    "INSERT INTO commerce_plan_entitlements "
                    "(id, plan_id, entitlement_code, limit_value, created_at, updated_at) "
                    "VALUES (:id, :plan_id, :code, :limit, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ).bindparams(id=ent_id, plan_id=FREE_PLAN_ID, code=code, limit=limit)
            )


def downgrade() -> None:
    op.drop_table("payment_webhook_events")
    op.drop_index("ix_refunds_transaction", table_name="payment_refunds")
    op.drop_table("payment_refunds")
    op.drop_index("ix_payments_provider_ref", table_name="payment_transactions")
    op.drop_index("ix_payments_org_status", table_name="payment_transactions")
    op.drop_table("payment_transactions")
    op.drop_index("ix_usage_records_org_feature", table_name="usage_records")
    op.drop_table("usage_records")
    op.drop_index("ix_invoices_org_status", table_name="commerce_invoices")
    op.drop_table("commerce_invoices")
    op.drop_index("ix_subscriptions_provider_ref", table_name="commerce_subscriptions")
    op.drop_index("ix_subscriptions_org_status", table_name="commerce_subscriptions")
    op.drop_table("commerce_subscriptions")
    op.drop_table("commerce_plan_entitlements")
    op.drop_table("commerce_plans")