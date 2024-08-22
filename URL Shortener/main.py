from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session    
from pydantic import BaseModel
import string
import random
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
import os

load_dotenv()  



templates = Jinja2Templates(directory="templates")


# Database setup
# Get the database URL from an environment variable, or use a default value
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
# Create a SQLAlchemy engine instance
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a SessionLocal class
# autocommit=False: Transactions are not automatically committed
# autoflush=False: Changes are not automatically flushed to the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for declarative models
Base = declarative_base()

# Define the URL model
class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, index=True)
    short_code = Column(String, unique=True, index=True)

# Create the database tables
Base.metadata.create_all(bind=engine)

# Pydantic model for request body validation
class URLInput(BaseModel):
    url: str

# Create a FastAPI instance
app = FastAPI()

# Dependency to get database session
def get_db():
    # Create a new database session
    db = SessionLocal()
    try:
        # Yield the session for use in the route function
        yield db
    finally:
        # Ensure the session is closed after the request is completed
        db.close()

# Generate a random short code
def generate_short_code(length=6):
    # Use ASCII letters and digits to create a random string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/shorten", response_class=HTMLResponse)
async def shorten_url(request: Request, url: str = Form(...), db: Session = Depends(get_db)):
    short_code = generate_short_code()
    db_url = URL(original_url=url, short_code=short_code)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    short_url = f"{request.base_url}{short_code}"
    return templates.TemplateResponse("index.html", {"request": request, "short_url": short_url})

@app.get("/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    db_url = db.query(URL).filter(URL.short_code == short_code).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return RedirectResponse(url=db_url.original_url)


@app.get("/docs", response_class=HTMLResponse)
async def read_documentation(request: Request):
    return templates.TemplateResponse("docs.html", {"request": request})