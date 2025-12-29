import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from werkzeug.security import generate_password_hash

def fix_auth():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'similarity_detector.db')
    db_manager = DatabaseManager(db_path)
    
    email = 'admin@airport.kr'
    password = '1234'
    username = 'admin_kr'
    
    print(f"Adding/Updating user: {email}")
    
    password_hash = generate_password_hash(password)
    
    query = """
    INSERT INTO admin_users (username, email, password_hash, role, allowed_tabs, is_active)
    VALUES (?, ?, ?, 'admin', '["*"]', 1)
    ON CONFLICT(email) DO UPDATE SET
        password_hash = excluded.password_hash,
        is_active = 1
    """
    
    try:
        db_manager.execute_insert(query, (username, email, password_hash))
        print("Successfully updated user credentials.")
        
        # Verify
        user = db_manager.get_admin_user_by_email(email)
        print(f"Verification: Found user {user['email']} with ID {user['id']}")
        
    except Exception as e:
        print(f"Error updating user: {e}")

if __name__ == "__main__":
    fix_auth()
