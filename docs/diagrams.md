# Use Case Diagram & System Architecture — Expense Tracker

## Use Case Diagram

**Actors:** Guest, User, Admin

### Guest
- UC1: Register (สมัครสมาชิก)
- UC2: Login (เข้าสู่ระบบ)

### User (ต้อง login ก่อน)
- UC3: View own expenses + summary (ดูรายการและยอดรวม)
- UC4: Create expense/income (เพิ่มรายการ)
- UC5: Edit expense (แก้ไขรายการ)
- UC6: Delete expense (ลบรายการ)
- UC7: Filter by type income/expense (กรองประเภท)
- UC8: Logout (ออกจากระบบ)

### Admin (extends User)
- UC9: View all users (ดู users ทั้งหมด)
- UC10: Delete user (ลบ user)
- UC11: View all expenses (ดูรายการทั้งหมดในระบบ)

---

## System Architecture

```
┌─────────────────────────────────────────────────┐
│                   Client Browser                │
│  (Jinja2 HTML + Tailwind CSS + Form submissions)│
└───────────────────┬─────────────────────────────┘
                    │ HTTPS
                    ▼
┌─────────────────────────────────────────────────┐
│         FastAPI  —  Render Web Service          │
│                                                 │
│  /login, /register     → Auth pages             │
│  /auth/login           → Set JWT cookie         │
│  /auth/register        → Create user            │
│  /auth/logout          → Clear cookie           │
│  /, /expenses/*        → Expense CRUD (User)    │
│  /admin/*              → Admin pages            │
│                                                 │
│  get_db()              → SQLAlchemy session     │
│  get_current_user()    → decode JWT cookie      │
└───────────────────┬─────────────────────────────┘
                    │ SQLAlchemy ORM
                    ▼
┌─────────────────────────────────────────────────┐
│       PostgreSQL  —  Render Managed DB          │
│                                                 │
│  users     (id, username, email,                │
│             hashed_password, role)              │
│  expenses  (id, title, amount, type,            │
│             category, date, owner_id)           │
└─────────────────────────────────────────────────┘
```

**Authentication Flow:**
1. POST /auth/login → FastAPI verify bcrypt password
2. FastAPI issue JWT (python-jose) with user_id + role
3. JWT stored in HTTP-only cookie (JS cannot access)
4. Every request sends cookie automatically → FastAPI decodes JWT
5. Admin routes check role == "admin" before allowing access
