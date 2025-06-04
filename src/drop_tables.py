# drop_tables.py

from sqlalchemy import text
from app.database import get_database_connection

def drop_all_tables():
    """Drop all tables in the correct order to respect foreign key constraints."""
    
    # Connect to the database
    engine = get_database_connection()
    
    try:
        with engine.connect() as connection:
            # Define the drop table statements in reverse dependency order
            # Child tables must be dropped before parent tables
            
            # 1. First drop tables with most dependencies
            connection.execute(text("DROP TABLE IF EXISTS TableStatus CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS Prompts_response CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS Prompts CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS AiDocumentation CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS DataManagementTable CASCADE;"))
            
            # 2. Drop boards
            connection.execute(text("DROP TABLE IF EXISTS Boards CASCADE;"))
            
            # 3. Drop main boards
            connection.execute(text("DROP TABLE IF EXISTS MainBoard CASCADE;"))
            
            # 4. Drop user-related tables
            connection.execute(text("DROP TABLE IF EXISTS OTPs CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS ClientUsers CASCADE;"))
            
            connection.commit()
            print("All tables have been dropped successfully.")
    
    except Exception as e:
        print(f"Error dropping tables: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    drop_all_tables()