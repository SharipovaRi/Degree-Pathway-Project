from fastapi import FastAPI, HTTPException   # For error handling
import asyncpg   # For PostgreDQL connection
import json  # To handle JSON data
from pydantic import BaseModel # Import Pydantic for data validation
from typing import List, Optional
import os   # os for environment var
from dotenv import load_dotenv  # To load .env files 
from fastapi.middleware.cors import CORSMiddleware




# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="DegreePath API", version="1.0.0")  #Handle all web request

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # CHANGE DOMAIN!!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = os.getenv("DB_HOST", "localhost")       
DB_PORT = os.getenv("DB_PORT", "5432")              
DB_NAME = os.getenv("DB_NAME")         
DB_USER = os.getenv("DB_USER")                    
DB_PASSWORD = os.getenv("DB_PASSWORD") 

# Build database URL from individual components
if DB_USER and DB_PASSWORD:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Fallback: check for full DATABASE_URL in environment
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("Database credentials not found! Please set DB_USER and DB_PASSWORD in .env file")
print(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")

# Pydantic Models - These define the structure of data coming in/out of our API

class CreateUser(BaseModel):
    """
    Model for creating a new user
    This ensures that when someone sends data to create a user,
    it has the required fields with correct types
    """
    email: str  # Required string field
    name: str   # Required string field

class User(BaseModel):
    """
    Model for user data coming out of database
    """
    id: int
    email: str
    name: str

class CreatePlan(BaseModel):
    """
    Model for creating a degree plan
    """
    program_id: int           # Which program this plan is for
    plan_data: dict          # The actual plan data (flexible JSON)

class Course(BaseModel):
    """
    Model for course data
    """
    id: int
    program_id: int
    code: str
    title: str
    credits: int
    offered_terms: List[str]      # List of strings like ["Fall", "Spring"]
    prerequisites: List[str]      # List of course codes

# To connect to database, create and return a connection to PostgreSQL DB and can be paused or resumed bc of async
async def get_database_connection():
    try:
        connection = await asyncpg.connect(DATABASE_URL)
        return connection
    except asyncpg.InvalidPasswordError:
        print("ERROR: Invalid database password")
        raise HTTPException(status_code=500, detail="Database authentication failed")
    except asyncpg.InvalidCatalogNameError:
        print(f"ERROR: Database '{DB_NAME}' does not exist")
        raise HTTPException(status_code=500, detail=f"Database '{DB_NAME}' not found")
    except asyncpg.ConnectionDoesNotExistError:
        print(f"ERROR: Cannot connect to database server at {DB_HOST}:{DB_PORT}")
        raise HTTPException(status_code=500, detail="Database server not reachable")
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
# Basic route 
@app.get("/")
def read_root():
    return {"message": "Degree Planner API", "status": "running"}  # Just to verify that API is working 

# Configuration check endpoint
@app.get("/config")
def check_config():
    """
    Check if environment variables are properly configured to debug
    """
    config_status = {
        "database": {
            "host": DB_HOST,
            "port": DB_PORT, 
            "name": DB_NAME,
            "user": DB_USER,
            "password_set": bool(DB_PASSWORD),  # Show if password exists, not the actual password
        },
        "environment_file_loaded": os.path.exists(".env"),
        "status": "OK" if DB_USER and DB_PASSWORD else "MISSING_CREDENTIALS"
    }
    
    if not DB_USER or not DB_PASSWORD:
        config_status["error"] = "DB_USER or DB_PASSWORD not set in environment"
    
    return config_status

# Test DB connection 
@app.get("/test-db")
async def test_database():
    try:
        # Connect to database
        conn = await get_database_connection()
        
        # See what database is connected to
        db_name = await conn.fetchval("SELECT current_database()")
        
        # Check if tables exist
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        tables = await conn.fetch(tables_query)
        table_names = [row['table_name'] for row in tables]
        
        # Try to count programs
        programs_count = None
        if 'programs' in table_names:
            programs_count = await conn.fetchval("SELECT COUNT(*) FROM programs")
        
        # Close connection 
        await conn.close()
        
        return {
            "status": "success", 
            "message": "Database connection working!",
            "database_name": db_name,
            "tables_found": table_names,
            "programs_count": programs_count
        }
        
    except Exception as e:
        # If anything goes wrong, return detailed error info
        return {
            "status": "error", 
            "message": f"Database error: {str(e)}",
            "database_url_format": f"postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            "connection_details": {
                "host": DB_HOST,
                "port": DB_PORT,
                "database": DB_NAME,
                "user": DB_USER
            }
        }
    
# Get all schools from DB
@app.get("/schools")
async def get_all_schools():
    conn = await get_database_connection()
    
    try:
        # SQL query to get unique school names, sorted alphabetically
        query = "SELECT DISTINCT school_name FROM programs ORDER BY school_name"
        
        rows = await conn.fetch(query)
        
        # Convert database rows to a simple list
        # Each row is like a dictionary with the school_name value
        schools = [row['school_name'] for row in rows]
        
        return {"schools": schools, "count": len(schools)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        # Close connection 
        await conn.close()

# Get programs for a specific school
@app.get("/schools/{school_name}/programs")
async def get_programs_for_school(school_name: str):

    conn = await get_database_connection()
    
    try:
        # SQL query with a parameter ($1 is a placeholder for school_name)
        query = """
        SELECT id, school_name, program_name, degree_type
        FROM programs 
        WHERE school_name = $1
        ORDER BY program_name
        """
        
        # Pass school_name as parameter, prevents SQL injection attacks
        rows = await conn.fetch(query, school_name)
        
        # Convert each row to a dictionary
        programs = [dict(row) for row in rows]
        
        return {
            "school": school_name,
            "programs": programs,
            "count": len(programs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()  # Close it 

# Create a user
@app.post("/users")
async def create_new_user(user_data: CreateUser):
    """
    Create a new user
    user_data will be automatically validated by Pydantic
    If the JSON doesn't match CreateUser model, FastAPI returns error automatically
    """
    conn = await get_database_connection()
    
    try:
        query = """
        INSERT INTO users (email, name)
        VALUES ($1, $2)
        RETURNING id, email, name
        """
        
        # Insert the new user and return the created user data
        row = await conn.fetchrow(query, user_data.email, user_data.name)
        
        return {
            "message": "User created successfully",
            "user": dict(row)
        }
        
    except asyncpg.UniqueViolationError:
        # This happens if email already exists (because email is UNIQUE in our table)
        raise HTTPException(status_code=400, detail="Email already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()

# Save a degree plan
@app.post("/users/{user_id}/plans")
async def save_degree_plan(user_id: int, plan_data: CreatePlan):
    """
    Save a degree plan for a user
    This combines path parameter (user_id) with POST data (plan_data)
    """
    conn = await get_database_connection()
    
    try:
        # First verify user exists
        user_check = await conn.fetchval("SELECT id FROM users WHERE id = $1", user_id)
        if not user_check:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify program exists  
        program_check = await conn.fetchval("SELECT id FROM programs WHERE id = $1", plan_data.program_id)
        if not program_check:
            raise HTTPException(status_code=404, detail="Program not found")
        
        # Save the plan
        query = """
        INSERT INTO plans (user_id, program_id, plan_data)
        VALUES ($1, $2, $3)
        RETURNING id, created_at
        """
        
        # Convert plan_data.plan_data (dict) to JSON string for database storage
        result = await conn.fetchrow(query, user_id, plan_data.program_id, json.dumps(plan_data.plan_data))
        
        return {
            "message": "Plan saved successfully",
            "plan_id": result['id'],
            "created_at": result['created_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()

# Get all plans for a user
@app.get("/users/{user_id}/plans")
async def get_user_plans(user_id: int):
    """Get all saved plans for a specific user"""
    conn = await get_database_connection()
    
    try:
        # Join plans with programs to get program details
        query = """
        SELECT 
            p.id, 
            p.user_id, 
            p.program_id, 
            p.plan_data, 
            p.created_at,
            pr.school_name, 
            pr.program_name, 
            pr.degree_type
        FROM plans p
        JOIN programs pr ON p.program_id = pr.id
        WHERE p.user_id = $1
        ORDER BY p.created_at DESC
        """
        
        rows = await conn.fetch(query, user_id)
        
        plans = []
        for row in rows:
            plan = dict(row)
            # Convert JSON string back to dict
            plan['plan_data'] = json.loads(plan['plan_data'])
            plans.append(plan)
        
        return {
            "user_id": user_id,
            "plans": plans,
            "count": len(plans)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()

# Get courses for a specific program
@app.get("/programs/{program_id}/courses")
async def get_courses_for_program(program_id: int):
    """
    Get all courses for a specific program
    program_id is converted to integer automatically by FastAPI
    """
    conn = await get_database_connection()
    
    try:
        # Verify the program exists
        program_query = "SELECT program_name, school_name FROM programs WHERE id = $1"
        program = await conn.fetchrow(program_query, program_id)
        
        if not program:
            # If program doesn't exist, return 404 error
            raise HTTPException(status_code=404, detail=f"Program with id {program_id} not found")
        
        # Get all courses for this program
        courses_query = """
        SELECT id, program_id, code, title, credits, offered_terms, prerequisites
        FROM courses 
        WHERE program_id = $1
        ORDER BY code
        """
        
        rows = await conn.fetch(courses_query, program_id)
        courses = [dict(row) for row in rows]
        
        return {
            "program_id": program_id,
            "program_name": program['program_name'],
            "school_name": program['school_name'],
            "courses": courses,
            "total_courses": len(courses)
        }
        
    except HTTPException:
        # Re-raise HTTPException (like 404) without changing it
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()

# Get all users
@app.get("/users")
async def get_all_users():
    """Get all users in the system"""
    conn = await get_database_connection()
    
    try:
        query = "SELECT id, email, name FROM users ORDER BY name"
        rows = await conn.fetch(query)
        users = [dict(row) for row in rows]
        
        return {"users": users, "count": len(users)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()

# Get specific user
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get a specific user by their ID"""
    conn = await get_database_connection()
    
    try:
        query = "SELECT id, email, name FROM users WHERE id = $1"
        row = await conn.fetchrow(query, user_id)
        
        if not row:
            raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
        
        return dict(row)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        await conn.close()