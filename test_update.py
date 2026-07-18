import sys
sys.path.append('.')
from src.database import SessionLocal, DocumentModel
import hashlib, re
from pathlib import Path

db = SessionLocal()
doc_id = 2 # The ID the user was editing
doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()

if not doc:
    print("Doc not found")
    sys.exit(1)

ten_moi = doc.name or "test"
chon_lv = "nhan_thuc"
chon_ab = "0-3"
chon_dt = "giao_an"
chon_tier = 1
chon_subs = ["sub1"]
chon_levels = ["lv1"]
url = doc.source_url

print(f"Before: {doc.status}, {doc.local_path}")

doc.name = ten_moi
doc.linh_vuc = chon_lv
doc.age_band = chon_ab
doc.doc_type = chon_dt
doc.source_tier = int(chon_tier)
doc.sub_domain_ids = ",".join(chon_subs)
doc.level_ids = ",".join(chon_levels)
doc.need_manual = False
doc.status = "exported"

short_hash = hashlib.md5(str(url).encode()).hexdigest()[:4].upper()
lv_m = {"nhan_thuc": "NT", "ngon_ngu": "NN", "tham_my": "TM", "the_chat": "TC", "tinh_cam_xh": "TX"}.get(chon_lv, "XX")
dt_m = chon_dt.split(".")[-1].upper()[:3] if "." in chon_dt else chon_dt[:3].upper()
doc.doc_code = f"DOC-{lv_m}-{chon_ab}-{dt_m}-{short_hash}"

old_path = Path(doc.local_path) if doc.local_path else None
if old_path and old_path.exists():
    with open(old_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_fields = {
        "name": ten_moi,
        "linh_vucs": [chon_lv],
        "age_bands": [chon_ab],
        "doc_type": chon_dt,
        "source_tier": int(chon_tier),
        "sub_domain_ids": chon_subs,
        "level_ids": chon_levels,
        "human_verified": "true"
    }
    
    parts = content.split("---", 2)
    if len(parts) >= 3:
        frontmatter = parts[1]
        body = parts[2]
        for k, v in new_fields.items():
            if isinstance(v, list):
                val_str = "[" + ", ".join([f'"{i}"' for i in v]) + "]"
            elif isinstance(v, str) and v not in ["true", "false"]:
                safe_v = v.replace('"', '\\"')
                val_str = f'"{safe_v}"'
            else:
                val_str = str(v)
            
            pat = r"(^" + k + r":).*$"
            if re.search(pat, frontmatter, flags=re.MULTILINE):
                frontmatter = re.sub(pat, f"{k}: {val_str}", frontmatter, flags=re.MULTILINE)
            else:
                if not frontmatter.endswith("\n"): frontmatter += "\n"
                frontmatter += f"{k}: {val_str}\n"
        
        new_content = f"---{frontmatter}---{body}"
        
        safe_name = re.sub(r'[^a-zA-Z0-9]+', '-', ten_moi.lower()).strip('-')
        new_slug = f"{doc.doc_code}__{safe_name}.md"
        new_path = old_path.parent / new_slug
        
        print(f"Writing to {new_path}")
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        if str(old_path) != str(new_path):
            old_path.unlink()
        
        doc.local_path = str(new_path)

db.commit()
print("Success")
