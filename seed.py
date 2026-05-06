from database import SessionLocal, engine
import models
from auth import hash_password

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()
admin = db.query(models.User).filter(models.User.username == "admin").first()
if not admin:
    db.add(models.User(
        username="admin",
        email="admin@expensetracker.com",
        hashed_password=hash_password("admin1234"),
        role="admin",
    ))
    db.commit()
    print("Admin created: username=admin, password=admin1234")
else:
    print("Admin already exists")
db.close()
