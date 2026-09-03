"""jobseeker career os: work dna, career goals, opportunities, applications

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-03

STRICTLY ADDITIVE and safe:
- Creates eleven brand-new canonical tables. Every table name is new — none
  exist in the shared Supabase careers schema (companies, jobs, applications,
  job_offers, ...), so nothing live is touched or renamed.
- Seeds a small demo opportunity corpus (provenance-marked
  ``imported_from = 'demo_careers_corpus_v1'``) so the jobseeker discovery and
  matching engine has controlled, realistic data in every environment. The
  seed is idempotent (keyed by source+slug) and clearly separated from the
  live careers corpus, which stays authoritative in Supabase.
Rollback drops exactly the objects this revision created.

New tables: work_dna_profiles, work_dna_answers, career_goals, opportunities,
            opportunity_interactions, job_applications, application_events,
            interviews, offers, career_milestones, user_notifications
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
now = sa.text("CURRENT_TIMESTAMP")
tz = sa.DateTime(timezone=True)

# Demo opportunity corpus — mirrors the shape of the AR Holdings careers
# corpus (portfolio brands + realistic engineering/commercial roles) so the
# matching engine is exercised against believable data in dev/test/prod.
# (company_id, company_name, title, slug, summary, country, city, work_mode,
#  employment_type, experience_level, seniority, industry, skills, salary_min,
#  salary_max, currency, remote_eligible, source)
DEMO_OPPORTUNITIES = [
    # --- Dot Protocol (blockchain infrastructure) ---------------------------
    (None, "Dot Protocol", "Senior Blockchain Engineer", "dot-protocol-senior-blockchain-engineer",
     "Own protocol architecture for Dot Protocol — consensus, smart contracts, and cross-chain bridges.",
     "UAE", "Dubai", "hybrid", "full_time", "5+ years", "senior", "Blockchain",
     ["blockchain", "solidity", "rust", "distributed systems", "cryptography"],
     120000, 180000, "USD", True, "demo_careers_corpus_v1"),
    (None, "Dot Protocol", "Protocol Research Engineer", "dot-protocol-research-engineer",
     "Design next-generation consensus mechanisms and formally verify core protocol invariants.",
     "UAE", "Dubai", "hybrid", "full_time", "3+ years", "mid", "Blockchain",
     ["rust", "research", "cryptography", "distributed systems", "mathematics"],
     90000, 140000, "USD", True, "demo_careers_corpus_v1"),
    (None, "Dot Protocol", "Smart Contract Auditor", "dot-protocol-smart-contract-auditor",
     "Audit smart contracts and security models across the Dot ecosystem.",
     "UAE", "Dubai", "remote", "full_time", "4+ years", "senior", "Blockchain",
     ["solidity", "security", "auditing", "web3", "python"],
     110000, 160000, "USD", True, "demo_careers_corpus_v1"),
    # --- Titan Capital (finance / investments) -------------------------------
    (None, "Titan Capital", "Investment Analyst", "titan-capital-investment-analyst",
     "Source and diligence high-growth technology investments across emerging markets.",
     "UAE", "Dubai", "onsite", "full_time", "2+ years", "mid", "Finance",
     ["financial modeling", "due diligence", "data analysis", "excel", "research"],
     70000, 100000, "USD", False, "demo_careers_corpus_v1"),
    (None, "Titan Capital", "Quantitative Researcher", "titan-capital-quant-researcher",
     "Build pricing and risk models for the Titan portfolio's digital asset strategies.",
     "UAE", "Dubai", "hybrid", "full_time", "3+ years", "mid", "Finance",
     ["python", "statistics", "machine learning", "quantitative analysis", "finance"],
     120000, 200000, "USD", True, "demo_careers_corpus_v1"),
    # --- Akuma (consumer AI) --------------------------------------------------
    (None, "Akuma", "Machine Learning Engineer", "akuma-ml-engineer",
     "Ship production ML systems powering Akuma's AI-first consumer products.",
     "UAE", "Dubai", "hybrid", "full_time", "3+ years", "mid", "AI / Software",
     ["python", "machine learning", "pytorch", "nlp", "aws"],
     90000, 150000, "USD", True, "demo_careers_corpus_v1"),
    (None, "Akuma", "Full-Stack Engineer (AI Products)", "akuma-fullstack-engineer",
     "Build end-to-end AI product experiences across web and mobile surfaces.",
     "UAE", "Dubai", "hybrid", "full_time", "2+ years", "mid", "AI / Software",
     ["typescript", "react", "node", "python", "graphql", "postgresql"],
     80000, 130000, "USD", True, "demo_careers_corpus_v1"),
    # --- Vault / fintech ------------------------------------------------------
    (None, "Vault", "Backend Engineer (Payments)", "vault-backend-payments-engineer",
     "Design resilient payment rails processing millions of transactions with strict compliance.",
     "UAE", "Abu Dhabi", "onsite", "full_time", "4+ years", "senior", "Fintech",
     ["python", "java", "distributed systems", "postgresql", "payments"],
     100000, 160000, "USD", False, "demo_careers_corpus_v1"),
    (None, "Vault", "Security Engineer", "vault-security-engineer",
     "Own application security, threat modelling, and compliance tooling for a regulated fintech.",
     "UAE", "Abu Dhabi", "hybrid", "full_time", "3+ years", "mid", "Fintech",
     ["security", "python", "aws", "penetration testing", "compliance"],
     95000, 145000, "USD", False, "demo_careers_corpus_v1"),
    # --- Cloud / infrastructure -------------------------------------------------
    (None, "Aurora Cloud", "Site Reliability Engineer", "aurora-cloud-sre",
     "Keep Aurora's global cloud platform reliable, observable, and fast.",
     "Saudi Arabia", "Riyadh", "remote", "full_time", "3+ years", "mid", "Cloud",
     ["kubernetes", "terraform", "aws", "linux", "python", "observability"],
     85000, 135000, "USD", True, "demo_careers_corpus_v1"),
    # --- AR Labs (applied research) ------------------------------------------
    (None, "AR Labs", "Applied AI Researcher", "ar-labs-applied-ai-researcher",
     "Advance applied NLP and recommendation research with direct product impact.",
     "UAE", "Dubai", "hybrid", "full_time", "4+ years", "senior", "AI / Research",
     ["python", "machine learning", "nlp", "transformers", "research", "pytorch"],
     130000, 200000, "USD", True, "demo_careers_corpus_v1"),
    # --- Commercial / growth roles -------------------------------------------
    (None, "AR Holdings", "Growth Product Manager", "ar-holdings-growth-pm",
     "Drive acquisition and activation across the AR portfolio's consumer products.",
     "UAE", "Dubai", "hybrid", "full_time", "3+ years", "mid", "Product",
     ["product management", "analytics", "sql", "a/b testing", "growth"],
     80000, 120000, "USD", False, "demo_careers_corpus_v1"),
    (None, "AR Holdings", "Brand Designer", "ar-holdings-brand-designer",
     "Shape premium brand experiences across the global AR portfolio.",
     "UAE", "Dubai", "onsite", "full_time", "3+ years", "mid", "Design",
     ["design", "figma", "brand identity", "typography", "illustration"],
     65000, 95000, "USD", False, "demo_careers_corpus_v1"),
    (None, "Titan Capital", "HR Business Partner", "titan-capital-hr-business-partner",
     "Run talent programs and people operations for a fast-scaling investment group.",
     "UAE", "Dubai", "onsite", "full_time", "4+ years", "senior", "People",
     ["hr operations", "recruiting", "employee relations", "compensation", "onboarding"],
     70000, 110000, "USD", False, "demo_careers_corpus_v1"),
    (None, "Aurora Cloud", "DevRel Engineer", "aurora-cloud-devrel",
     "Build the developer community and technical content for Aurora's platform.",
     "Kenya", "Nairobi", "remote", "full_time", "2+ years", "mid", "Cloud",
     ["technical writing", "public speaking", "typescript", "python", "developer tools"],
     60000, 95000, "USD", True, "demo_careers_corpus_v1"),
]


def upgrade() -> None:
    # ---- Work DNA ----------------------------------------------------------
    op.create_table(
        "work_dna_profiles",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("source", sa.String(40), nullable=False, server_default="assessment"),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("dimensions", sa.JSON()),
        sa.Column("completed_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("person_id", "version", name="uq_work_dna_person_version"),
    )
    op.create_index("ix_work_dna_profiles_person_id", "work_dna_profiles", ["person_id"])

    op.create_table(
        "work_dna_answers",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "profile_id", uuid_type,
            sa.ForeignKey("work_dna_profiles.id", ondelete="SET NULL"),
        ),
        sa.Column("question_key", sa.String(80), nullable=False),
        sa.Column("answer", sa.JSON()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_work_dna_answers_person_id", "work_dna_answers", ["person_id"])

    # ---- Career goals ------------------------------------------------------
    op.create_table(
        "career_goals",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("target_role", sa.String(200)),
        sa.Column("target_industries", sa.JSON()),
        sa.Column("target_locations", sa.JSON()),
        sa.Column("preferred_work_modes", sa.JSON()),
        sa.Column("min_salary", sa.Float()),
        sa.Column("salary_currency", sa.String(8), server_default="USD"),
        sa.Column("open_to_relocation", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("open_to_remote", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("availability", sa.String(120)),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_career_goals_person_id", "career_goals", ["person_id"])

    # ---- Opportunities -----------------------------------------------------
    op.create_table(
        "opportunities",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "company_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220)),
        sa.Column("summary", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("location", sa.String(200)),
        sa.Column("country", sa.String(80)),
        sa.Column("city", sa.String(120)),
        sa.Column("remote_eligible", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("work_mode", sa.String(20)),
        sa.Column("employment_type", sa.String(32)),
        sa.Column("experience_level", sa.String(80)),
        sa.Column("seniority", sa.String(40)),
        sa.Column("industry", sa.String(120)),
        sa.Column("skills_required", sa.JSON()),
        sa.Column("min_salary", sa.Float()),
        sa.Column("max_salary", sa.Float()),
        sa.Column("salary_currency", sa.String(8), server_default="USD"),
        sa.Column("language_requirements", sa.JSON()),
        sa.Column("closing_at", sa.Date()),
        sa.Column("source", sa.String(24), nullable=False, server_default="platform"),
        sa.Column("imported_from", sa.String(120)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_opportunities_company_id", "opportunities", ["company_id"])
    op.create_index("ix_opportunities_company_name", "opportunities", ["company_name"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    # ---- Opportunity interactions (person's save/dismiss) -------------------
    op.create_table(
        "opportunity_interactions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "opportunity_id", uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint(
            "person_id", "opportunity_id",
            name="uq_opportunity_interactions_person_opp",
        ),
    )
    op.create_index(
        "ix_opportunity_interactions_person_id",
        "opportunity_interactions", ["person_id"],
    )
    op.create_index(
        "ix_opportunity_interactions_opportunity_id",
        "opportunity_interactions", ["opportunity_id"],
    )

    # ---- Applications -------------------------------------------------------
    op.create_table(
        "job_applications",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "opportunity_id", uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="discovered"
        ),
        sa.Column("cover_note", sa.Text()),
        sa.Column("applied_at", tz),
        sa.Column("withdrawn_at", tz),
        sa.Column("last_activity_at", tz, server_default=now, nullable=False),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint(
            "person_id", "opportunity_id",
            name="uq_applications_person_opportunity",
        ),
    )
    op.create_index("ix_job_applications_person_id", "job_applications", ["person_id"])
    op.create_index(
        "ix_job_applications_opportunity_id", "job_applications", ["opportunity_id"]
    )

    op.create_table(
        "application_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "application_id", uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column(
            "actor_user_id", uuid_type,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_application_events_application_id", "application_events", ["application_id"]
    )

    # ---- Interviews ----------------------------------------------------------
    op.create_table(
        "interviews",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "application_id", uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("scheduled_at", tz, nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("mode", sa.String(16), nullable=False, server_default="video"),
        sa.Column("meeting_link", sa.String(500)),
        sa.Column("interviewer_name", sa.String(200)),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(24), nullable=False, server_default="scheduled"),
        sa.Column("reschedule_reason", sa.Text()),
        sa.Column("reschedule_requested_at", tz),
        sa.Column("reschedule_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_interviews_application_id", "interviews", ["application_id"])

    # ---- Offers ----------------------------------------------------------------
    op.create_table(
        "offers",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "application_id", uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("salary_amount", sa.Float()),
        sa.Column("salary_currency", sa.String(8), server_default="USD"),
        sa.Column("equity", sa.String(120)),
        sa.Column("benefits_summary", sa.Text()),
        sa.Column("start_date", sa.Date()),
        sa.Column("location", sa.String(200)),
        sa.Column("terms_summary", sa.Text()),
        sa.Column("offer_document_id", uuid_type),
        sa.Column("responded_at", tz),
        sa.Column("expires_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_offers_application_id", "offers", ["application_id"])

    # ---- Career milestones -----------------------------------------------------
    op.create_table(
        "career_milestones",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("reference_type", sa.String(60)),
        sa.Column("reference_id", sa.String(64)),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_career_milestones_person_id", "career_milestones", ["person_id"])

    # ---- Notifications ----------------------------------------------------------
    op.create_table(
        "user_notifications",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id", uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False, server_default="system"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("read_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])

    # ---- Demo opportunity seed (idempotent, provenance-marked) -----------------
    # Uses a Core table object (not raw text) so UUID/list/float values are
    # coerced properly across SQLite and Postgres dialects.
    opportunities = sa.table(
        "opportunities",
        sa.column("id", uuid_type),
        sa.column("company_id", uuid_type),
        sa.column("company_name", sa.String),
        sa.column("title", sa.String),
        sa.column("slug", sa.String),
        sa.column("summary", sa.Text),
        sa.column("country", sa.String),
        sa.column("city", sa.String),
        sa.column("work_mode", sa.String),
        sa.column("employment_type", sa.String),
        sa.column("experience_level", sa.String),
        sa.column("seniority", sa.String),
        sa.column("industry", sa.String),
        sa.column("skills_required", sa.JSON),
        sa.column("min_salary", sa.Float),
        sa.column("max_salary", sa.Float),
        sa.column("salary_currency", sa.String),
        sa.column("remote_eligible", sa.Boolean),
        sa.column("source", sa.String),
        sa.column("imported_from", sa.String),
        sa.column("status", sa.String),
        sa.column("is_approved", sa.Boolean),
    )
    conn = op.get_bind()
    for (company_id, company_name, title, slug, summary, country, city, work_mode,
         employment_type, experience_level, seniority, industry, skills,
         salary_min, salary_max, currency, remote_eligible, source) in DEMO_OPPORTUNITIES:
        existing = conn.execute(
            sa.select(sa.literal(1)).select_from(opportunities).where(
                opportunities.c.source == source,
                opportunities.c.slug == slug,
            )
        ).first()
        if existing is not None:
            continue
        conn.execute(
            opportunities.insert().values(
                id=uuid.uuid4(),
                company_id=company_id,
                company_name=company_name,
                title=title,
                slug=slug,
                summary=summary,
                country=country,
                city=city,
                work_mode=work_mode,
                employment_type=employment_type,
                experience_level=experience_level,
                seniority=seniority,
                industry=industry,
                skills_required=skills,
                min_salary=salary_min,
                max_salary=salary_max,
                salary_currency=currency,
                remote_eligible=remote_eligible,
                source=source,
                imported_from="demo_careers_corpus_v1",
                status="active",
                is_approved=True,
            )
        )


def downgrade() -> None:
    op.drop_table("user_notifications")
    op.drop_index("ix_career_milestones_person_id", table_name="career_milestones")
    op.drop_table("career_milestones")
    op.drop_index("ix_offers_application_id", table_name="offers")
    op.drop_table("offers")
    op.drop_index("ix_interviews_application_id", table_name="interviews")
    op.drop_table("interviews")
    op.drop_index("ix_application_events_application_id", table_name="application_events")
    op.drop_table("application_events")
    op.drop_index(
        "ix_job_applications_opportunity_id", table_name="job_applications"
    )
    op.drop_index("ix_job_applications_person_id", table_name="job_applications")
    op.drop_table("job_applications")
    op.drop_table("opportunity_interactions")
    op.drop_index("ix_opportunities_status", table_name="opportunities")
    op.drop_index("ix_opportunities_company_name", table_name="opportunities")
    op.drop_index("ix_opportunities_company_id", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index("ix_career_goals_person_id", table_name="career_goals")
    op.drop_table("career_goals")
    op.drop_index("ix_work_dna_answers_person_id", table_name="work_dna_answers")
    op.drop_table("work_dna_answers")
    op.drop_index("ix_work_dna_profiles_person_id", table_name="work_dna_profiles")
    op.drop_table("work_dna_profiles")
