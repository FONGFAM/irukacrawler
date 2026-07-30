import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import pandas as pd
from pathlib import Path

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/export/docscrawlerdb.sqlite")

if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_code = Column(String, index=True)
    name = Column(String)
    source_url = Column(String, index=True)
    local_path = Column(String)
    linh_vuc = Column(String)
    age_band = Column(String)
    doc_type = Column(String)
    source_tier = Column(Integer)
    sub_domain_ids = Column(Text)
    level_ids = Column(Text)
    game_assets_potential = Column(Text)
    uploaded_at = Column(DateTime)
    status = Column(String)
    need_manual = Column(Boolean, default=False)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_from_csv():
    manifest_path = Path("data/export/manifest.csv")
    if not manifest_path.exists() or manifest_path.stat().st_size == 0:
        return
    
    # Read CSV
    df = pd.read_csv(manifest_path)
    
    # Check if table has data
    from sqlalchemy import text as st
    with engine.connect() as conn:
        count = conn.execute(st("SELECT COUNT(*) FROM documents")).scalar()
    
    if count == 0:
        print("Migrating data from CSV to PostgreSQL...")
        # Handle uploaded_at
        if "uploaded_at" in df.columns:
            df["uploaded_at"] = pd.to_datetime(df["uploaded_at"], errors="coerce")
            
        # Ensure boolean
        if "need_manual" in df.columns:
            df["need_manual"] = df["need_manual"].astype(str).str.lower() == "true"
            
        # Clean doc_code if NA
        df["doc_code"] = df["doc_code"].fillna("NEED_MANUAL_MIGRATED")
        
        # Write to SQL
        df.to_sql("documents", engine, if_exists="append", index=False)
        print("Migration complete. Renaming manifest.csv to manifest.csv.bak")
        manifest_path.rename(manifest_path.with_suffix(".csv.bak"))
    else:
        print("Database already contains data, skipping migration.")

if __name__ == "__main__":
    init_db()
    migrate_from_csv()
