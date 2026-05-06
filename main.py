import os
from pathlib import Path
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from database import engine, SessionLocal
from auth import hash_password, verify_password, create_access_token, decode_token

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return db.query(models.User).filter(models.User.id == int(payload["sub"])).first()


# -- Auth routes -------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/auth/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}
        )
    token = create_access_token(user.id, user.role)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=86400)
    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/auth/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == email)
    ).first()
    if existing:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": "ชื่อผู้ใช้หรืออีเมลนี้มีอยู่แล้ว"}
        )
    user = models.User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role="user",
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/login", status_code=303)


@app.post("/auth/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response


# -- Expense routes ----------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    type_filter = request.query_params.get("type", "")
    query = db.query(models.Expense).filter(models.Expense.owner_id == current_user.id)
    if type_filter:
        query = query.filter(models.Expense.type == type_filter)
    expenses = query.order_by(models.Expense.date.desc()).all()
    total_income = sum(e.amount for e in db.query(models.Expense).filter(
        models.Expense.owner_id == current_user.id,
        models.Expense.type == "income"
    ).all())
    total_expense = sum(e.amount for e in db.query(models.Expense).filter(
        models.Expense.owner_id == current_user.id,
        models.Expense.type == "expense"
    ).all())
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "expenses": expenses,
        "type_filter": type_filter,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
    })


@app.get("/expenses/create", response_class=HTMLResponse)
def expense_create_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("expense_form.html", {
        "request": request, "user": current_user, "expense": None
    })


@app.post("/expenses")
def expense_create(
    request: Request,
    title: str = Form(...),
    amount: float = Form(...),
    type: str = Form("expense"),
    category: str = Form(""),
    date: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    from datetime import date as date_type
    expense = models.Expense(
        title=title,
        amount=amount,
        type=type,
        category=category or None,
        date=date_type.fromisoformat(date),
        note=note or None,
        owner_id=current_user.id,
    )
    db.add(expense)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.get("/expenses/{expense_id}/edit", response_class=HTMLResponse)
def expense_edit_page(expense_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    expense = db.get(models.Expense, expense_id)
    if not expense or expense.owner_id != current_user.id:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("expense_form.html", {
        "request": request, "user": current_user, "expense": expense
    })


@app.post("/expenses/{expense_id}")
def expense_update(
    expense_id: int,
    request: Request,
    title: str = Form(...),
    amount: float = Form(...),
    type: str = Form("expense"),
    category: str = Form(""),
    date: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    expense = db.get(models.Expense, expense_id)
    if not expense or expense.owner_id != current_user.id:
        return RedirectResponse("/", status_code=303)
    from datetime import date as date_type
    expense.title = title
    expense.amount = amount
    expense.type = type
    expense.category = category or None
    expense.date = date_type.fromisoformat(date)
    expense.note = note or None
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/expenses/{expense_id}/delete")
def expense_delete(expense_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    expense = db.get(models.Expense, expense_id)
    if expense and expense.owner_id == current_user.id:
        db.delete(expense)
        db.commit()
    return RedirectResponse("/", status_code=303)


# -- Admin routes ------------------------------------------------------------

@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse("/", status_code=303)
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return templates.TemplateResponse("admin_users.html", {
        "request": request, "user": current_user, "users": users
    })


@app.post("/admin/users/{user_id}/delete")
def admin_delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse("/", status_code=303)
    if user_id == current_user.id:
        return RedirectResponse("/admin/users", status_code=303)
    user = db.get(models.User, user_id)
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.get("/admin/expenses", response_class=HTMLResponse)
def admin_expenses(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user or current_user.role != "admin":
        return RedirectResponse("/", status_code=303)
    expenses = db.query(models.Expense).order_by(models.Expense.date.desc()).all()
    return templates.TemplateResponse("admin_expenses.html", {
        "request": request, "user": current_user, "expenses": expenses
    })
