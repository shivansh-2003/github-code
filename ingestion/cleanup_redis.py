#!/usr/bin/env python3
"""
Script to clean up Redis data
"""

from redis_imple import RedisRepoStorage

def show_all_users():
    """Show all users in Redis"""
    print("👥 Users found in Redis:")
    
    storage = RedisRepoStorage()
    all_keys = storage.redis_client.keys("user:*:repos:list")
    
    users = []
    for key in all_keys:
        user_id = key.split(":")[1]
        repos = storage.redis_client.smembers(key)
        users.append((user_id, len(repos)))
        print(f"   🔹 User ID: {user_id} ({len(repos)} repos)")
        
        # Try to find the original email by checking test emails
        test_emails = ["test@example.com", "quicktest@example.com", "user@example.com"]
        for email in test_emails:
            if storage._generate_user_id(email) == user_id:
                print(f"      ↳ Original email: {email}")
                break
    
    return users

def delete_specific_repo(user_email, repo_name):
    """Delete a specific repository for a user"""
    print(f"🗑️ Deleting repository: {repo_name} for user: {user_email}")
    
    storage = RedisRepoStorage()
    repo_name_redis = repo_name.replace('/', '_')
    
    success = storage.delete_user_repository(user_email, repo_name_redis)
    
    if success:
        print("✅ Repository deleted successfully")
    else:
        print("❌ Failed to delete repository")
    
    return success

def delete_all_user_data(user_identifier):
    """Delete ALL data for a user (accepts email or user ID)"""
    print(f"🗑️ Deleting ALL data for user: {user_identifier}")
    
    storage = RedisRepoStorage()
    
    # Check if it's a user ID (12 chars, hex) or email
    if len(user_identifier) == 12 and all(c in '0123456789abcdef' for c in user_identifier):
        # It's a user ID, find the email
        test_emails = ["test@example.com", "quicktest@example.com", "user@example.com"]
        user_email = None
        for email in test_emails:
            if storage._generate_user_id(email) == user_identifier:
                user_email = email
                break
        
        if not user_email:
            print(f"❌ Could not find original email for user ID: {user_identifier}")
            return False
            
        print(f"📧 Found original email: {user_email}")
    else:
        user_email = user_identifier
    
    success = storage.delete_all_user_data(user_email)
    
    if success:
        print("✅ All user data deleted successfully")
    else:
        print("❌ Failed to delete user data")
    
    return success

def delete_all_test_data():
    """Delete all test data we created"""
    print("🧹 Cleaning up all test data...")
    
    # Delete test users
    delete_all_user_data("test@example.com")
    delete_all_user_data("quicktest@example.com")
    
    print("✅ Cleanup complete!")

def delete_by_user_id_direct(user_id):
    """Delete data directly by user ID (bypasses email lookup)"""
    print(f"🗑️ Deleting data for user ID: {user_id}")
    
    storage = RedisRepoStorage()
    
    # Get all keys for this user ID
    pattern = f"user:{user_id}:*"
    keys = storage.redis_client.keys(pattern)
    
    if not keys:
        print(f"❌ No data found for user ID: {user_id}")
        return False
    
    # Delete all keys
    deleted = storage.redis_client.delete(*keys)
    print(f"🗑️ Deleted {deleted} keys")
    print("✅ Data deleted successfully!")
    
    return True

def delete_everything():
    """Delete EVERYTHING in Redis (be careful!)"""
    print("⚠️  This will delete ALL data in Redis!")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm == "DELETE ALL":
        storage = RedisRepoStorage()
        all_keys = storage.redis_client.keys("user:*")
        
        if all_keys:
            deleted = storage.redis_client.delete(*all_keys)
            print(f"🗑️ Deleted {deleted} keys")
            print("✅ All data deleted!")
        else:
            print("ℹ️ No data found to delete")
    else:
        print("❌ Deletion cancelled")

if __name__ == "__main__":
    print("🗑️ Redis Cleanup Options")
    print("0. Show all users in Redis")
    print("1. Delete specific repo")
    print("2. Delete all data for a user") 
    print("3. Delete all test data")
    print("4. Delete by user ID (direct)")
    print("5. Delete EVERYTHING (dangerous!)")
    
    choice = input("\nEnter choice (0-5): ")
    
    if choice == "0":
        show_all_users()
    elif choice == "1":
        show_all_users()
        user_email = input("\nUser email: ")
        repo_name = input("Repository name (owner/repo): ")
        delete_specific_repo(user_email, repo_name)
    elif choice == "2":
        show_all_users()
        user_input = input("\nEnter user email OR user ID: ")
        delete_all_user_data(user_input)
    elif choice == "3":
        delete_all_test_data()
    elif choice == "4":
        show_all_users()
        user_id = input("\nEnter user ID to delete: ")
        delete_by_user_id_direct(user_id)
    elif choice == "5":
        delete_everything()
    else:
        print("Invalid choice") 