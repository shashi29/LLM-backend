# # database_migration.py
# from sqlalchemy import text
# from app.database import get_database_connection

# def migrate_mainboard_unique_constraint():
#     """
#     Migration script to update the MainBoard table constraint.
#     Run this once to update existing databases.
#     """
#     connection = get_database_connection()
    
#     try:
#         with connection.connect() as cursor:
#             # Drop the old unique constraint
#             cursor.execute(text("""
#                 ALTER TABLE MainBoard DROP CONSTRAINT IF EXISTS mainboard_name_key;
#             """))
            
#             # Add the new composite unique constraint
#             cursor.execute(text("""
#                 ALTER TABLE MainBoard ADD CONSTRAINT mainboard_client_name_unique 
#                 UNIQUE (client_user_id, name);
#             """))
            
#             cursor.commit()
#             print("Migration completed successfully!")
            
#     except Exception as e:
#         print(f"Migration failed: {e}")
#     finally:
#         connection.dispose()

# if __name__ == "__main__":
#     migrate_mainboard_unique_constraint()

from sqlalchemy import text
from app.database import get_database_connection

def migrate_email_verified_column():
    """
    Migration script to add the email_verified column to the ClientUsers table.
    Run this once to update existing databases.
    """
    connection = get_database_connection()
    
    try:
        with connection.connect() as cursor:
            cursor.execute(text("""
                ALTER TABLE ClientUsers 
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
            """))
            cursor.commit()
            print("Migration executed successfully!")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        connection.dispose()
        
migrate_email_verified_column()