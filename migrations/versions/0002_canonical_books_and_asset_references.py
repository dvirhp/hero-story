"""canonical books and asset references"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def _postgres_guards():
    """Frozen PostgreSQL invariants; not a replacement for typed domain validation."""
    op.execute("""
CREATE FUNCTION storyforge_book_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.state <> 'draft' OR NEW.revision <> 1 OR NEW.created_at <> NEW.updated_at THEN
      RAISE EXCEPTION 'BOOK_INITIAL_STATE_INVALID' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
  END IF;
  IF TG_OP = 'DELETE' THEN
    IF OLD.state <> 'draft' THEN
      RAISE EXCEPTION 'BOOK_IMMUTABLE' USING ERRCODE = '23514';
    END IF;
    RETURN OLD;
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.creation_mode IS DISTINCT FROM OLD.creation_mode
     OR NEW.source_story_id IS DISTINCT FROM OLD.source_story_id
     OR NEW.source_snapshot IS DISTINCT FROM OLD.source_snapshot
     OR NEW.language IS DISTINCT FROM OLD.language OR NEW.direction IS DISTINCT FROM OLD.direction
     OR NEW.schema_version IS DISTINCT FROM OLD.schema_version OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'BOOK_ORIGIN_IMMUTABLE' USING ERRCODE = '23514';
  END IF;
  IF NEW.revision <> OLD.revision + 1 OR NEW.updated_at < OLD.updated_at THEN
    RAISE EXCEPTION 'BOOK_REVISION_INVALID' USING ERRCODE = '23514';
  END IF;
  IF OLD.state = 'archived' OR (OLD.state = 'finalized' AND
     (NEW.state <> 'archived' OR NEW.title IS DISTINCT FROM OLD.title OR NEW.finalized_at IS DISTINCT FROM OLD.finalized_at)) THEN
    RAISE EXCEPTION 'BOOK_IMMUTABLE' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER guard_book BEFORE INSERT OR UPDATE OR DELETE ON books FOR EACH ROW EXECUTE FUNCTION storyforge_book_guard()")
    op.execute("""
CREATE FUNCTION storyforge_book_child_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bid uuid; parent_state text;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.book_id IS DISTINCT FROM OLD.book_id THEN
    RAISE EXCEPTION 'BOOK_PAGE_MOVE_FORBIDDEN' USING ERRCODE = '23514';
  END IF;
  bid := CASE WHEN TG_OP = 'DELETE' THEN OLD.book_id ELSE NEW.book_id END;
  SELECT state INTO parent_state FROM books WHERE id = bid FOR UPDATE;
  IF parent_state IS NOT NULL AND parent_state <> 'draft' THEN
    RAISE EXCEPTION 'BOOK_PAGES_IMMUTABLE' USING ERRCODE = '23514';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$
""")
    for table in ("book_pages", "book_page_assets"):
        op.execute(f"CREATE TRIGGER guard_{table} BEFORE INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION storyforge_book_child_guard()")
    op.execute("""
CREATE FUNCTION storyforge_asset_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (to_jsonb(NEW) - 'state') IS DISTINCT FROM (to_jsonb(OLD) - 'state') THEN
    RAISE EXCEPTION 'ASSET_REFERENCE_IMMUTABLE' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER guard_asset BEFORE UPDATE ON assets FOR EACH ROW EXECUTE FUNCTION storyforge_asset_guard()")
    op.execute("""
CREATE FUNCTION storyforge_source_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE sid uuid;
BEGIN
  IF TG_TABLE_NAME = 'stories' THEN sid := OLD.id;
  ELSIF TG_OP = 'INSERT' THEN sid := NEW.story_id;
  ELSE sid := OLD.story_id;
  END IF;
  IF EXISTS (SELECT 1 FROM books WHERE source_story_id = sid) THEN
    RAISE EXCEPTION 'BOOK_SOURCE_IMMUTABLE' USING ERRCODE = '23514';
  END IF;
  IF TG_TABLE_NAME = 'story_pages' AND TG_OP = 'UPDATE' THEN
    IF EXISTS (SELECT 1 FROM books WHERE source_story_id = NEW.story_id) THEN
      RAISE EXCEPTION 'BOOK_SOURCE_IMMUTABLE' USING ERRCODE = '23514';
    END IF;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER guard_projected_story BEFORE UPDATE OR DELETE ON stories FOR EACH ROW EXECUTE FUNCTION storyforge_source_guard()")
    op.execute("CREATE TRIGGER guard_projected_story_pages BEFORE INSERT OR UPDATE OR DELETE ON story_pages FOR EACH ROW EXECUTE FUNCTION storyforge_source_guard()")
    op.execute("""
CREATE FUNCTION storyforge_book_aggregate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bid uuid; b books%ROWTYPE; n integer; lo integer; hi integer; page_row record;
BEGIN
  IF TG_TABLE_NAME = 'books' THEN
    bid := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
  ELSE
    bid := CASE WHEN TG_OP = 'DELETE' THEN OLD.book_id ELSE NEW.book_id END;
  END IF;
  SELECT * INTO b FROM books WHERE id = bid;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT count(*), min(position), max(position) INTO n, lo, hi FROM book_pages WHERE book_id = bid;
  IF (n > 0 AND (lo <> 1 OR hi <> n)) OR (b.state = 'finalized' AND n = 0) THEN
    RAISE EXCEPTION 'BOOK_PAGE_SEQUENCE_INVALID' USING ERRCODE = '23514';
  END IF;
  FOR page_row IN SELECT document FROM book_pages WHERE book_id = bid LOOP
    IF jsonb_typeof(page_row.document) <> 'object' OR page_row.document->>'schema_version' IS DISTINCT FROM '1'
       OR jsonb_typeof(page_row.document->'blocks') IS DISTINCT FROM 'array' THEN
      RAISE EXCEPTION 'BOOK_DOCUMENT_INVALID' USING ERRCODE = '23514';
    END IF;
    IF jsonb_array_length(page_row.document->'blocks') = 0 THEN
      RAISE EXCEPTION 'BOOK_DOCUMENT_INVALID' USING ERRCODE = '23514';
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM book_pages bp, LATERAL jsonb_array_elements(bp.document->'blocks') block
      WHERE bp.book_id = bid AND block->>'kind' = 'image' AND NOT EXISTS (
        SELECT 1 FROM book_page_assets a WHERE a.book_id = bid AND a.page_id = bp.id AND a.slot_key = block->>'slot_key'))
     OR EXISTS (SELECT 1 FROM book_page_assets a JOIN book_pages bp ON bp.id = a.page_id
      WHERE a.book_id = bid AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(bp.document->'blocks') block
        WHERE block->>'kind' = 'image' AND block->>'slot_key' = a.slot_key)) THEN
    RAISE EXCEPTION 'BOOK_ASSET_BINDINGS_INVALID' USING ERRCODE = '23514';
  END IF;
  IF b.creation_mode = 'AI_GENERATED' THEN
    IF NOT EXISTS (SELECT 1 FROM stories s WHERE s.id = b.source_story_id AND s.status = 'completed') THEN
      RAISE EXCEPTION 'BOOK_SOURCE_NOT_COMPLETED' USING ERRCODE = '23514';
    END IF;
    IF b.revision = 1 THEN
      IF n <> (SELECT page_count FROM stories WHERE id = b.source_story_id) OR n = 0 OR EXISTS (
        SELECT 1 FROM book_pages p LEFT JOIN story_pages s ON s.story_id = b.source_story_id AND s.page_number = p.position
        WHERE p.book_id = bid AND (s.page_number IS NULL OR p.source_page_key IS DISTINCT FROM s.page_id
          OR p.source_target_id IS DISTINCT FROM s.target_id
          OR p.document->'blocks'->0->'sentence_units' IS DISTINCT FROM s.sentence_units::jsonb)) THEN
        RAISE EXCEPTION 'BOOK_SOURCE_PAGES_MISMATCH' USING ERRCODE = '23514';
      END IF;
    END IF;
  END IF;
  RETURN NULL;
END $$
""")
    for table in ("books", "book_pages", "book_page_assets"):
        op.execute(f"CREATE CONSTRAINT TRIGGER check_{table}_aggregate AFTER INSERT OR UPDATE OR DELETE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION storyforge_book_aggregate()")

def upgrade():
    op.create_table('assets',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('storage_backend', sa.String(length=32), nullable=False),
    sa.Column('object_key', sa.String(length=160), nullable=False),
    sa.Column('checksum', sa.String(length=64), nullable=False),
    sa.Column('media_type', sa.String(length=32), nullable=False),
    sa.Column('byte_size', sa.BigInteger(), nullable=False),
    sa.Column('width', sa.Integer(), nullable=False),
    sa.Column('height', sa.Integer(), nullable=False),
    sa.Column('scope', sa.String(length=32), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.CheckConstraint("media_type IN ('image/png','image/jpeg','image/webp')", name='ck_asset_type'),
    sa.CheckConstraint("scope IN ('public_editorial','private')", name='ck_asset_scope'),
    sa.CheckConstraint("state IN ('ready','blocked')", name='ck_asset_state'),
    sa.CheckConstraint("storage_backend IN ('local','object_store')", name='ck_asset_backend'),
    sa.CheckConstraint('byte_size > 0 AND width > 0 AND height > 0', name='ck_asset_size'),
    sa.CheckConstraint('length(checksum) = 64', name='ck_asset_checksum'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_backend', 'object_key', name='uq_asset_object')
    )
    op.create_table('books',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('schema_version', sa.String(length=16), nullable=False),
    sa.Column('creation_mode', sa.String(length=32), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('revision', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('language', sa.String(length=16), nullable=False),
    sa.Column('direction', sa.String(length=3), nullable=False),
    sa.Column('source_story_id', sa.Uuid(), nullable=True),
    sa.Column('source_snapshot', sa.JSON(none_as_null=True).with_variant(postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("(creation_mode = 'MANUAL' AND source_story_id IS NULL AND source_snapshot IS NULL) OR (creation_mode = 'AI_GENERATED' AND source_story_id IS NOT NULL AND source_snapshot IS NOT NULL)", name='ck_book_origin'),
    sa.CheckConstraint("(language = 'en' AND direction = 'ltr') OR (language = 'he' AND direction = 'rtl')", name='ck_book_direction'),
    sa.CheckConstraint("(state = 'draft' AND finalized_at IS NULL AND archived_at IS NULL) OR (state = 'finalized' AND finalized_at IS NOT NULL AND archived_at IS NULL) OR (state = 'archived' AND archived_at IS NOT NULL)", name='ck_book_lifecycle_time'),
    sa.CheckConstraint("creation_mode IN ('AI_GENERATED','MANUAL')", name='ck_book_mode_m1'),
    sa.CheckConstraint("schema_version = '1'", name='ck_book_schema'),
    sa.CheckConstraint("state IN ('draft','finalized','archived')", name='ck_book_state'),
    sa.CheckConstraint('length(title) BETWEEN 1 AND 120 AND length(trim(title)) > 0', name='ck_book_title'),
    sa.CheckConstraint('revision >= 1', name='ck_book_revision'),
    sa.CheckConstraint('updated_at >= created_at', name='ck_book_time_order'),
    sa.CheckConstraint('finalized_at IS NULL OR (finalized_at >= created_at AND finalized_at <= updated_at)', name='ck_book_finalized_time'),
    sa.CheckConstraint('archived_at IS NULL OR (archived_at >= created_at AND archived_at <= updated_at)', name='ck_book_archived_time'),
    sa.ForeignKeyConstraint(['source_story_id'], ['stories.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_story_id')
    )
    op.create_index('ix_books_created', 'books', ['created_at', 'id'], unique=False)
    op.create_table('book_pages',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('book_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('document_schema_version', sa.String(length=16), nullable=False),
    sa.Column('document', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('source_page_key', sa.String(length=120), nullable=True),
    sa.Column('source_target_id', sa.String(length=120), nullable=True),
    sa.CheckConstraint("document_schema_version = '1'", name='ck_book_page_schema'),
    sa.CheckConstraint('position > 0', name='ck_book_page_position'),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('book_id', 'id', name='uq_book_page_identity'),
    (sa.UniqueConstraint('book_id', 'position', deferrable=True, initially='IMMEDIATE', name='uq_book_page_position')
     if op.get_bind().dialect.name == 'postgresql' else
     sa.UniqueConstraint('book_id', 'position', name='uq_book_page_position_sqlite')),
    sa.UniqueConstraint('book_id', 'source_page_key', name='uq_book_source_page')
    )
    op.create_index(op.f('ix_book_pages_book_id'), 'book_pages', ['book_id'], unique=False)
    op.create_table('book_page_assets',
    sa.Column('book_id', sa.Uuid(), nullable=False),
    sa.Column('page_id', sa.Uuid(), nullable=False),
    sa.Column('slot_key', sa.String(length=120), nullable=False),
    sa.Column('asset_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['book_id', 'page_id'], ['book_pages.book_id', 'book_pages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('book_id', 'page_id', 'slot_key')
    )
    op.create_index(op.f('ix_book_page_assets_asset_id'), 'book_page_assets', ['asset_id'], unique=False)
    if op.get_bind().dialect.name == "postgresql":
        _postgres_guards()

def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for name in ("storyforge_book_aggregate", "storyforge_book_child_guard", "storyforge_book_guard", "storyforge_asset_guard", "storyforge_source_guard"):
            op.execute(f"DROP FUNCTION {name}() CASCADE")
    op.drop_index(op.f('ix_book_page_assets_asset_id'), table_name='book_page_assets')
    op.drop_table('book_page_assets')
    op.drop_index(op.f('ix_book_pages_book_id'), table_name='book_pages')
    op.drop_table('book_pages')
    op.drop_index('ix_books_created', table_name='books')
    op.drop_table('books')
    op.drop_table('assets')
