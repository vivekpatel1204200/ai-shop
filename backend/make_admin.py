from database import SessionLocal
import models

email = input("Enter the email to promote to admin: ")

db = SessionLocal()
user = db.query(models.User).filter(models.User.email == email).first()

if not user:
    print("No user found with that email.")
else:
    user.role = "admin"
    db.commit()
    print(f"{user.email} is now an admin.")

db.close()