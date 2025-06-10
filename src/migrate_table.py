# database_migration.py
from sqlalchemy import text
from app.database import get_database_connection

def migrate_mainboard_unique_constraint():
    """
    Migration script to update the MainBoard table constraint.
    Run this once to update existing databases.
    """
    connection = get_database_connection()
    
    try:
        with connection.connect() as cursor:
            # Drop the old unique constraint
            cursor.execute(text("""
                ALTER TABLE MainBoard DROP CONSTRAINT IF EXISTS mainboard_name_key;
            """))
            
            # Add the new composite unique constraint
            cursor.execute(text("""
                ALTER TABLE MainBoard ADD CONSTRAINT mainboard_client_name_unique 
                UNIQUE (client_user_id, name);
            """))
            
            cursor.commit()
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        connection.dispose()

if __name__ == "__main__":
    migrate_mainboard_unique_constraint()