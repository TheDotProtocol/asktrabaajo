"""talent graph: skill taxonomy, evidence, career paths, talent pools

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-03

STRICTLY ADDITIVE and safe:
- Extends canonical ``skills`` with nullable taxonomy columns
  (subcategory, description, status) — existing rows unaffected.
- Creates eight brand-new canonical tables (aliases, relationships,
  evidence, opportunity requirements, career paths + steps, talent pools,
  pool members, saved candidates, search events).
- Seeds a provenance-marked starter taxonomy (skills, aliases,
  relationships) and advisory career paths — all idempotent by primary key.
- Inserts Phase 7 permissions (candidates.search, pools.manage) and role
  mappings into the canonical RBAC catalog.
None of these names exist in the live Supabase careers schema, so nothing
legacy is touched. Rollback drops exactly what this revision created.

New tables: skill_aliases, skill_relationships, skill_evidence,
            opportunity_requirements, career_paths, career_path_steps,
            talent_pools, talent_pool_members, saved_candidates,
            candidate_search_events
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
now = sa.text("CURRENT_TIMESTAMP")
tz = sa.DateTime(timezone=True)

NEW_PERMISSIONS = [
    ("candidates.search", "Search the talent graph for discoverable candidates"),
    ("pools.manage", "Create and manage talent pools and saved candidates"),
]
ROLE_ADDITIONS = {
    "org_admin": ["candidates.search", "pools.manage"],
    "hr": ["candidates.search", "pools.manage"],
    "recruiter": ["candidates.search", "pools.manage"],
}


def _normalize(text: str) -> str:
    """Mirror of services/skills_registry.normalize() — keep in sync."""
    token = text.lower().strip().replace(".", "")
    return " ".join(token.split())


# (canonical name, category, subcategory) — starter taxonomy.
SKILLS = [
    # Software engineering
    ("JavaScript", "software_engineering", "frontend"),
    ("TypeScript", "software_engineering", "frontend"),
    ("React", "software_engineering", "frontend"),
    ("React Native", "software_engineering", "mobile"),
    ("Next.js", "software_engineering", "frontend"),
    ("Vue.js", "software_engineering", "frontend"),
    ("HTML", "software_engineering", "frontend"),
    ("CSS", "software_engineering", "frontend"),
    ("Tailwind CSS", "software_engineering", "frontend"),
    ("Node.js", "software_engineering", "backend"),
    ("Python", "software_engineering", "backend"),
    ("Django", "software_engineering", "backend"),
    ("Flask", "software_engineering", "backend"),
    ("FastAPI", "software_engineering", "backend"),
    ("Java", "software_engineering", "backend"),
    ("Spring Boot", "software_engineering", "backend"),
    ("Go", "software_engineering", "backend"),
    ("Ruby", "software_engineering", "backend"),
    ("PHP", "software_engineering", "backend"),
    ("Laravel", "software_engineering", "backend"),
    ("C#", "software_engineering", "backend"),
    ("C++", "software_engineering", "backend"),
    ("SQL", "software_engineering", "data"),
    ("PostgreSQL", "software_engineering", "data"),
    ("MySQL", "software_engineering", "data"),
    ("MongoDB", "software_engineering", "data"),
    ("Redis", "software_engineering", "data"),
    ("GraphQL", "software_engineering", "api"),
    ("REST APIs", "software_engineering", "api"),
    ("Docker", "software_engineering", "devops"),
    ("Kubernetes", "software_engineering", "devops"),
    ("AWS", "software_engineering", "cloud"),
    ("GCP", "software_engineering", "cloud"),
    ("Azure", "software_engineering", "cloud"),
    ("Git", "software_engineering", "tooling"),
    ("CI/CD", "software_engineering", "devops"),
    ("System Design", "software_engineering", "architecture"),
    ("Microservices", "software_engineering", "architecture"),
    ("Testing", "software_engineering", "quality"),
    ("Blockchain", "software_engineering", "web3"),
    ("Smart Contracts", "software_engineering", "web3"),
    ("Solidity", "software_engineering", "web3"),
    # AI / data
    ("Machine Learning", "ai", "ml"),
    ("Deep Learning", "ai", "ml"),
    ("Generative AI", "ai", "genai"),
    ("Prompt Engineering", "ai", "genai"),
    ("OpenAI API", "ai", "genai"),
    ("Natural Language Processing", "ai", "ml"),
    ("Data Science", "ai", "data"),
    ("Data Analysis", "ai", "data"),
    ("Big Data", "ai", "data"),
    # Design
    ("UI/UX Design", "design", "ux"),
    ("Figma", "design", "ux"),
    ("Product Design", "design", "ux"),
    ("Wireframing", "design", "ux"),
    ("Brand Design", "design", "brand"),
    # Marketing / growth
    ("Digital Marketing", "marketing", "growth"),
    ("SEO", "marketing", "growth"),
    ("Content Writing", "marketing", "content"),
    ("Copywriting", "marketing", "content"),
    ("Social Media Marketing", "marketing", "social"),
    ("Email Marketing", "marketing", "growth"),
    ("Analytics", "marketing", "measurement"),
    # Sales / customer
    ("Sales", "sales", "sales"),
    ("Business Development", "sales", "sales"),
    ("Account Management", "sales", "customer"),
    ("Customer Success", "sales", "customer"),
    ("Customer Service", "sales", "customer"),
    ("Lead Generation", "sales", "sales"),
    # Hospitality
    ("Hospitality Operations", "hospitality", "operations"),
    ("Front Office", "hospitality", "operations"),
    ("Hotel Operations", "hospitality", "operations"),
    ("Food & Beverage", "hospitality", "operations"),
    ("Housekeeping", "hospitality", "operations"),
    ("Event Management", "hospitality", "operations"),
    ("Tourism Management", "hospitality", "operations"),
    # Healthcare
    ("Nursing", "healthcare", "nursing"),
    ("Critical Care", "healthcare", "nursing"),
    ("Healthcare Administration", "healthcare", "administration"),
    ("Medical Records", "healthcare", "administration"),
    # Construction / real estate
    ("Construction Management", "construction", "management"),
    ("Civil Engineering", "construction", "engineering"),
    ("Site Supervision", "construction", "site"),
    ("Quantity Surveying", "construction", "commercial"),
    ("Architecture", "construction", "design"),
    ("Project Management", "general", "delivery"),
    # Finance
    ("Accounting", "finance", "accounting"),
    ("Bookkeeping", "finance", "accounting"),
    ("Financial Analysis", "finance", "analysis"),
    ("Auditing", "finance", "accounting"),
    ("Taxation", "finance", "tax"),
    ("Payroll", "finance", "operations"),
    # HR / people
    ("Recruitment", "hr", "talent"),
    ("Talent Acquisition", "hr", "talent"),
    ("HR Operations", "hr", "operations"),
    ("People Management", "hr", "people"),
    ("Performance Management", "hr", "people"),
    # Leadership / professional
    ("Leadership", "leadership", "leadership"),
    ("Team Management", "leadership", "leadership"),
    ("Communication", "leadership", "professional"),
    ("Problem Solving", "leadership", "professional"),
    ("Agile", "leadership", "delivery"),
    ("Scrum", "leadership", "delivery"),
    ("Public Speaking", "leadership", "professional"),
    # Education
    ("Teaching", "education", "teaching"),
    ("Curriculum Design", "education", "teaching"),
    ("E-Learning", "education", "teaching"),
    # Umbrella taxonomy nodes (parents for relationships above).
    ("Frontend Development", "software_engineering", "frontend"),
    ("Backend Development", "software_engineering", "backend"),
    ("Web Development", "software_engineering", "frontend"),
    ("Mobile Development", "software_engineering", "mobile"),
    ("DevOps", "software_engineering", "devops"),
    ("Cloud Computing", "software_engineering", "cloud"),
    ("Databases", "software_engineering", "data"),
    ("Artificial Intelligence", "ai", "ml"),
    ("Healthcare", "healthcare", "general"),
    ("Construction", "construction", "general"),
    ("Management", "general", "leadership"),
]

# Alias token (normalized) -> canonical name (adds spellings normalization
# rules do not produce, e.g. space-less compounds).
EXTRA_ALIASES = {
    "reactjs": "React",
    "reactnative": "React Native",
    "nodejs": "Node.js",
    "nextjs": "Next.js",
    "typescript": "TypeScript",
    "postgresql": "PostgreSQL",
    "restapi": "REST APIs",
    "csharp": "C#",
    "cpp": "C++",
    "awscloud": "AWS",
}

# (child, parent, kind) — kind=parent means child is a specialization of
# parent. related/complementary are adjacency edges between equals.
RELATIONSHIPS = [
    ("React", "Frontend Development", "parent"),
    ("TypeScript", "Frontend Development", "parent"),
    ("React", "JavaScript", "parent"),
    ("TypeScript", "JavaScript", "parent"),
    ("JavaScript", "Web Development", "parent"),
    ("HTML", "Web Development", "parent"),
    ("CSS", "Web Development", "parent"),
    ("Next.js", "React", "parent"),
    ("React Native", "Mobile Development", "parent"),
    ("Node.js", "Backend Development", "parent"),
    ("Python", "Backend Development", "parent"),
    ("Django", "Python", "parent"),
    ("Flask", "Python", "parent"),
    ("FastAPI", "Python", "parent"),
    ("Machine Learning", "Artificial Intelligence", "parent"),
    ("Deep Learning", "Machine Learning", "parent"),
    ("Generative AI", "Machine Learning", "parent"),
    ("Natural Language Processing", "Machine Learning", "parent"),
    ("PostgreSQL", "Databases", "parent"),
    ("MySQL", "Databases", "parent"),
    ("MongoDB", "Databases", "parent"),
    ("Docker", "DevOps", "parent"),
    ("Kubernetes", "DevOps", "parent"),
    ("CI/CD", "DevOps", "parent"),
    ("AWS", "Cloud Computing", "parent"),
    ("GCP", "Cloud Computing", "parent"),
    ("Azure", "Cloud Computing", "parent"),
    ("Nursing", "Healthcare", "parent"),
    ("Civil Engineering", "Construction", "parent"),
    ("Project Management", "Management", "parent"),
    ("People Management", "Management", "parent"),
    ("TypeScript", "React", "complementary"),
    ("SQL", "Python", "complementary"),
    ("Figma", "UI/UX Design", "parent"),
    ("Docker", "Kubernetes", "complementary"),
    ("Git", "CI/CD", "complementary"),
    ("Agile", "Scrum", "related"),
    ("Digital Marketing", "SEO", "parent"),
    ("Customer Service", "Hospitality Operations", "related"),
    ("Front Office", "Hotel Operations", "parent"),
]

# Advisory career-path catalogue (title, target_role, industry, steps).
# Each step: role_title, seniority, [canonical skill names], short note.
CAREER_PATHS = [
    (
        "Frontend Engineering",
        "Engineering Manager",
        "software",
        [
            ("Junior Frontend Developer", "junior",
             ["JavaScript", "React", "HTML", "CSS", "Git"],
             "Build and ship UI features under guidance."),
            ("Frontend Developer", "mid",
             ["TypeScript", "React", "REST APIs", "Testing"],
             "Own frontend features end to end."),
            ("Senior Frontend Developer", "senior",
             ["TypeScript", "System Design", "Performance", "Mentoring"],
             "Lead complex frontends and mentor peers."),
            ("Frontend Lead", "lead",
             ["System Design", "People Management", "Architecture"],
             "Own the frontend platform and a small team."),
            ("Engineering Manager", "manager",
             ["People Management", "Project Management", "Recruitment"],
             "Lead engineers and deliver team outcomes."),
        ],
    ),
    (
        "Hospitality Operations",
        "General Manager",
        "hospitality",
        [
            ("Front Office Executive", "entry",
             ["Customer Service", "Front Office", "Communication"],
             "Run front desk operations."),
            ("Duty Manager", "junior",
             ["Front Office", "Hospitality Operations", "Problem Solving"],
             "Oversee daily hotel operations on shift."),
            ("Hotel Operations Manager", "mid",
             ["Hotel Operations", "People Management", "Budgeting"],
             "Manage hotel departments end to end."),
            ("General Manager", "senior",
             ["Hotel Operations", "Leadership", "Financial Analysis"],
             "Own hotel performance and guest experience."),
        ],
    ),
    (
        "Nursing & Care",
        "Nurse Unit Manager",
        "healthcare",
        [
            ("Registered Nurse", "entry",
             ["Nursing", "Critical Care", "Communication"],
             "Deliver patient care."),
            ("Senior Nurse", "mid",
             ["Critical Care", "Nursing", "Team Management"],
             "Lead care teams on shift."),
            ("Nurse Unit Manager", "senior",
             ["Healthcare Administration", "People Management", "Nursing"],
             "Run a clinical unit and its team."),
        ],
    ),
    (
        "Construction Delivery",
        "Construction Manager",
        "construction",
        [
            ("Site Engineer", "junior",
             ["Civil Engineering", "Construction Management", "Problem Solving"],
             "Supervise site technical works."),
            ("Site Supervisor", "mid",
             ["Site Supervision", "Project Management", "Construction Management"],
             "Run site operations to programme."),
            ("Construction Manager", "senior",
             ["Construction Management", "People Management", "Budgeting"],
             "Deliver projects on time and budget."),
        ],
    ),
    (
        "Data & Analytics",
        "Data Science Lead",
        "software",
        [
            ("Data Analyst", "junior",
             ["SQL", "Data Analysis", "Analytics"],
             "Answer business questions from data."),
            ("Data Scientist", "mid",
             ["Python", "Machine Learning", "Statistics", "SQL"],
             "Build models that inform decisions."),
            ("Data Science Lead", "senior",
             ["Machine Learning", "People Management", "Product Design"],
             "Own the analytics roadmap and a team."),
        ],
    ),
]


def _lookup_skill(conn, skills_table, name: str):
    row = conn.execute(
        sa.select(skills_table.c.id, skills_table.c.name).where(
            sa.func.lower(skills_table.c.name) == name.lower()
        )
    ).first()
    return row


def upgrade() -> None:
    conn = op.get_bind()

    # ---- skills: nullable taxonomy columns -----------------------------------
    op.add_column("skills", sa.Column("subcategory", sa.String(160)))
    op.add_column("skills", sa.Column("description", sa.Text()))
    op.add_column(
        "skills", sa.Column("status", sa.String(20), server_default="active",
                            nullable=False)
    )

    # ---- skill_aliases -------------------------------------------------------
    op.create_table(
        "skill_aliases",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "skill_id", uuid_type, sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(200), nullable=False, unique=True),
        sa.Column("original", sa.String(200)),
        sa.Column("source", sa.String(40), nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Float()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_skill_aliases_skill_id", "skill_aliases", ["skill_id"])

    # ---- skill_relationships -------------------------------------------------
    op.create_table(
        "skill_relationships",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "skill_id", uuid_type, sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_skill_id", uuid_type,
            sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("skill_id", "related_skill_id", "kind",
                            name="uq_skill_relationships_edge"),
    )
    op.create_index("ix_skill_relationships_skill_id", "skill_relationships", ["skill_id"])
    op.create_index(
        "ix_skill_relationships_related_skill_id", "skill_relationships",
        ["related_skill_id"],
    )

    # ---- skill_evidence ------------------------------------------------------
    op.create_table(
        "skill_evidence",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "skill_id", uuid_type, sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(24), nullable=False,
                  server_default="self"),
        sa.Column("reference_type", sa.String(40), nullable=False),
        sa.Column("reference_id", uuid_type, nullable=False),
        sa.Column("source", sa.String(60), nullable=False, server_default="work_id"),
        sa.Column("verification_status", sa.String(20), nullable=False,
                  server_default="unverified"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("person_id", "skill_id", "reference_type",
                            "reference_id", name="uq_skill_evidence_source"),
    )
    op.create_index("ix_skill_evidence_person_id", "skill_evidence", ["person_id"])
    op.create_index("ix_skill_evidence_skill_id", "skill_evidence", ["skill_id"])

    # ---- opportunity_requirements --------------------------------------------
    op.create_table(
        "opportunity_requirements",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "opportunity_id", uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "skill_id", uuid_type, sa.ForeignKey("skills.id", ondelete="SET NULL"),
        ),
        sa.Column("raw_text", sa.String(400), nullable=False),
        sa.Column("requirement_kind", sa.String(16), nullable=False,
                  server_default="required"),
        sa.Column("min_years", sa.Float()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("opportunity_id", "raw_text",
                            name="uq_opp_requirement_text"),
    )
    op.create_index(
        "ix_opportunity_requirements_opportunity_id",
        "opportunity_requirements", ["opportunity_id"],
    )

    # ---- career_paths + steps --------------------------------------------------
    op.create_table(
        "career_paths",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("target_role", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(120)),
        sa.Column("description", sa.Text()),
        sa.Column("source", sa.String(60), nullable=False,
                  server_default="asktrabaajo_career_paths_v1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_table(
        "career_path_steps",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "path_id", uuid_type, sa.ForeignKey("career_paths.id",
                                                ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("role_title", sa.String(200), nullable=False),
        sa.Column("seniority", sa.String(40)),
        sa.Column("description", sa.Text()),
        sa.Column("skills_required", sa.JSON()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("path_id", "step_order", name="uq_career_path_step_order"),
    )
    op.create_index("ix_career_path_steps_path_id", "career_path_steps", ["path_id"])
    op.create_index("ix_career_path_steps_role_title", "career_path_steps", ["role_title"])

    # ---- talent pools -----------------------------------------------------------
    op.create_table(
        "talent_pools",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "created_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_talent_pools_org_name"),
    )
    op.create_index("ix_talent_pools_organization_id", "talent_pools", ["organization_id"])

    # ---- talent pool members -----------------------------------------------------
    op.create_table(
        "talent_pool_members",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "pool_id", uuid_type, sa.ForeignKey("talent_pools.id",
                                                ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "added_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("pool_id", "person_id", name="uq_talent_pool_members"),
    )
    op.create_index("ix_talent_pool_members_pool_id", "talent_pool_members", ["pool_id"])
    op.create_index("ix_talent_pool_members_person_id", "talent_pool_members", ["person_id"])

    # ---- saved candidates --------------------------------------------------------
    op.create_table(
        "saved_candidates",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("note", sa.Text()),
        sa.Column("tags", sa.JSON()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", "person_id",
                            name="uq_saved_candidates_org_user_person"),
    )
    op.create_index("ix_saved_candidates_organization_id", "saved_candidates", ["organization_id"])
    op.create_index("ix_saved_candidates_user_id", "saved_candidates", ["user_id"])
    op.create_index("ix_saved_candidates_person_id", "saved_candidates", ["person_id"])

    # ---- candidate search events ----------------------------------------------------
    op.create_table(
        "candidate_search_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query", sa.String(300)),
        sa.Column("filters", sa.JSON()),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_candidate_search_events_organization_id", "candidate_search_events",
        ["organization_id"],
    )
    op.create_index(
        "ix_candidate_search_events_user_id", "candidate_search_events", ["user_id"],
    )

    # ---- seed taxonomy ---------------------------------------------------------
    skills_table = sa.table(
        "skills",
        sa.column("id", uuid_type),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("subcategory", sa.String),
        sa.column("description", sa.Text),
        sa.column("status", sa.String),
    )
    aliases_table = sa.table(
        "skill_aliases",
        sa.column("id", uuid_type),
        sa.column("skill_id", uuid_type),
        sa.column("alias", sa.String),
        sa.column("original", sa.String),
        sa.column("source", sa.String),
    )
    skill_ids: dict = {}
    for name, category, subcategory in SKILLS:
        existing = _lookup_skill(conn, skills_table, name)
        if existing is None:
            new_id = uuid.uuid4()
            conn.execute(
                skills_table.insert().values(
                    id=new_id, name=name, category=category,
                    subcategory=subcategory, status="active",
                )
            )
            skill_ids[name.lower()] = str(new_id)
        else:
            skill_ids[name.lower()] = str(existing.id)
            # Fill null taxonomy grouping without overwriting user data.
            conn.execute(
                skills_table.update()
                .where(skills_table.c.id == existing.id)
                .values(
                    category=sa.func.coalesce(skills_table.c.category, category),
                    subcategory=sa.func.coalesce(skills_table.c.subcategory, subcategory),
                    status=sa.func.coalesce(skills_table.c.status, "active"),
                )
            )
    # Canonical alias for each seeded skill + curated extra spellings.
    alias_rows = []
    for name, _cat, _sub in SKILLS:
        token = _normalize(name)
        alias_rows.append((skill_ids[name.lower()], token, name, "taxonomy_seed"))
    for token, canonical_name in EXTRA_ALIASES.items():
        key = canonical_name.lower()
        if key in skill_ids:
            alias_rows.append((skill_ids[key], token, token, "taxonomy_seed"))
    for skill_id, token, original, source in alias_rows:
        exists = conn.execute(
            sa.select(sa.literal(1)).select_from(aliases_table).where(
                aliases_table.c.alias == token
            )
        ).first()
        if exists is None:
            conn.execute(
                aliases_table.insert().values(
                    id=uuid.uuid4(), skill_id=uuid.UUID(skill_id), alias=token,
                    original=original, source=source,
                )
            )

    # ---- seed relationships ----------------------------------------------------
    rel_table = sa.table(
        "skill_relationships",
        sa.column("id", uuid_type),
        sa.column("skill_id", uuid_type),
        sa.column("related_skill_id", uuid_type),
        sa.column("kind", sa.String),
    )
    for child_name, parent_name, kind in RELATIONSHIPS:
        child_id = skill_ids.get(child_name.lower())
        parent_id = skill_ids.get(parent_name.lower())
        if child_id is None or parent_id is None:
            continue  # parent may be a non-seeded umbrella term
        exists = conn.execute(
            sa.select(sa.literal(1)).select_from(rel_table).where(
                rel_table.c.skill_id == uuid.UUID(child_id),
                rel_table.c.related_skill_id == uuid.UUID(parent_id),
                rel_table.c.kind == kind,
            )
        ).first()
        if exists is None:
            conn.execute(
                rel_table.insert().values(
                    id=uuid.uuid4(),
                    skill_id=uuid.UUID(child_id),
                    related_skill_id=uuid.UUID(parent_id),
                    kind=kind,
                )
            )

    # ---- seed career paths -------------------------------------------------------
    paths_table = sa.table(
        "career_paths",
        sa.column("id", uuid_type),
        sa.column("title", sa.String),
        sa.column("target_role", sa.String),
        sa.column("industry", sa.String),
        sa.column("description", sa.Text),
        sa.column("source", sa.String),
        sa.column("status", sa.String),
    )
    steps_table = sa.table(
        "career_path_steps",
        sa.column("id", uuid_type),
        sa.column("path_id", uuid_type),
        sa.column("step_order", sa.Integer),
        sa.column("role_title", sa.String),
        sa.column("seniority", sa.String),
        sa.column("description", sa.Text),
        sa.column("skills_required", sa.JSON),
    )
    for title, target_role, industry, steps in CAREER_PATHS:
        exists = conn.execute(
            sa.select(sa.literal(1)).select_from(paths_table).where(
                paths_table.c.title == title, paths_table.c.target_role == target_role
            )
        ).first()
        if exists is not None:
            continue
        path_id = uuid.uuid4()
        conn.execute(
            paths_table.insert().values(
                id=path_id, title=title, target_role=target_role,
                industry=industry,
                description=(
                    f"Advisory path toward {target_role}. Career movement is "
                    "never deterministic — steps signal common rungs, not guarantees."
                ),
                source="asktrabaajo_career_paths_v1", status="active",
            )
        )
        for order, (role_title, seniority, skills, note) in enumerate(steps):
            conn.execute(
                steps_table.insert().values(
                    id=uuid.uuid4(), path_id=path_id, step_order=order,
                    role_title=role_title, seniority=seniority,
                    skills_required=skills, description=note,
                )
            )

    # ---- RBAC: Phase 7 talent permissions -----------------------------------------
    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
    )
    for code, name in NEW_PERMISSIONS:
        exists = conn.execute(
            sa.select(sa.literal(1)).select_from(permissions_table).where(
                permissions_table.c.code == code
            )
        ).first()
        if exists is None:
            conn.execute(permissions_table.insert().values(code=code, name=name))

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    for role_code, codes in ROLE_ADDITIONS.items():
        for permission_code in codes:
            exists = conn.execute(
                sa.select(sa.literal(1)).select_from(role_permissions).where(
                    role_permissions.c.role_code == role_code,
                    role_permissions.c.permission_code == permission_code,
                )
            ).first()
            if exists is None:
                conn.execute(
                    role_permissions.insert().values(
                        role_code=role_code, permission_code=permission_code
                    )
                )


def downgrade() -> None:
    conn = op.get_bind()
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String),
    )
    for role_code, codes in ROLE_ADDITIONS.items():
        for permission_code in codes:
            conn.execute(
                role_permissions.delete().where(
                    role_permissions.c.role_code == role_code,
                    role_permissions.c.permission_code == permission_code,
                )
            )
    for code, _name in NEW_PERMISSIONS:
        conn.execute(permissions_table.delete().where(permissions_table.c.code == code))

    op.drop_index("ix_candidate_search_events_user_id", table_name="candidate_search_events")
    op.drop_index("ix_candidate_search_events_organization_id", table_name="candidate_search_events")
    op.drop_table("candidate_search_events")
    op.drop_index("ix_saved_candidates_person_id", table_name="saved_candidates")
    op.drop_index("ix_saved_candidates_user_id", table_name="saved_candidates")
    op.drop_index("ix_saved_candidates_organization_id", table_name="saved_candidates")
    op.drop_table("saved_candidates")
    op.drop_index("ix_talent_pool_members_person_id", table_name="talent_pool_members")
    op.drop_index("ix_talent_pool_members_pool_id", table_name="talent_pool_members")
    op.drop_table("talent_pool_members")
    op.drop_index("ix_talent_pools_organization_id", table_name="talent_pools")
    op.drop_table("talent_pools")
    op.drop_index("ix_career_path_steps_role_title", table_name="career_path_steps")
    op.drop_index("ix_career_path_steps_path_id", table_name="career_path_steps")
    op.drop_table("career_path_steps")
    op.drop_table("career_paths")
    op.drop_index(
        "ix_opportunity_requirements_opportunity_id", "opportunity_requirements"
    )
    op.drop_table("opportunity_requirements")
    op.drop_index("ix_skill_evidence_skill_id", table_name="skill_evidence")
    op.drop_index("ix_skill_evidence_person_id", table_name="skill_evidence")
    op.drop_table("skill_evidence")
    op.drop_index(
        "ix_skill_relationships_related_skill_id", "skill_relationships"
    )
    op.drop_index("ix_skill_relationships_skill_id", "skill_relationships")
    op.drop_table("skill_relationships")
    op.drop_index("ix_skill_aliases_skill_id", "skill_aliases")
    op.drop_table("skill_aliases")
    op.drop_column("skills", "status")
    op.drop_column("skills", "description")
    op.drop_column("skills", "subcategory")
