#!/usr/bin/env python3
"""
Minimal test script for the entire pipeline:
ingestion.py (download) -> redis.py (store in Redis Cloud)
"""

import os
import sys
from github import Github
from dotenv import load_dotenv

# Import directly since we're in the ingestion directory
from ingestion import download_repo_contents
from redis_imple import RedisRepoStorage

load_dotenv()

def test_pipeline():
    """Test the complete pipeline: GitHub download -> Redis storage"""
    
    print("🧪 Testing GitHub -> Redis Pipeline")
    print("=" * 50)
    
    # Configuration
    test_repo = "shivansh-2003/memo"  # Small repo for testing
    user_email = "test@example.com"
    local_path = "./test_downloaded_repo"
    
    try:
        # Step 1: Test GitHub connection
        print("1️⃣ Testing GitHub connection...")
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            print("❌ GITHUB_ACCESS_TOKEN not found in .env file")
            return False
        
        g = Github(github_token)
        repo = g.get_repo(test_repo)
        print(f"✅ Connected to GitHub, found repo: {repo.full_name}")
        
        # Step 2: Test download with ingestion.py
        print("\n2️⃣ Testing repository download...")
        download_repo_contents(repo, local_path)
        
        # Verify download worked
        if os.path.exists(local_path):
            file_count = sum([len(files) for r, d, files in os.walk(local_path)])
            print(f"✅ Download successful: {file_count} files downloaded to {local_path}")
        else:
            print("❌ Download failed: local path doesn't exist")
            return False
        
        # Step 3: Test Redis storage
        print("\n3️⃣ Testing Redis Cloud storage...")
        storage = RedisRepoStorage()
        
        success = storage.store_local_repo_to_redis(
            user_identifier=user_email,
            repo_full_name=test_repo,
            local_repo_path=local_path
        )
        
        if not success:
            print("❌ Redis storage failed")
            return False
        
        # Step 4: Verify Redis storage
        print("\n4️⃣ Verifying Redis storage...")
        repos = storage.get_user_repositories(user_email)
        
        if repos:
            for repo_info in repos:
                if repo_info['repo_full_name'] == test_repo:
                    print(f"✅ Verified in Redis: {repo_info['total_files']} files, {repo_info['total_size_bytes']} bytes")
                    break
        else:
            print("❌ No repositories found in Redis")
            return False
        
        # Step 5: Test retrieval
        print("\n5️⃣ Testing file retrieval from Redis...")
        repo_name = test_repo.replace('/', '_')
        repo_data = storage.get_repository_files(user_email, repo_name)
        
        if 'error' in repo_data:
            print(f"❌ Error retrieving files: {repo_data['error']}")
            return False
        
        print(f"✅ Retrieved {len(repo_data['files'])} files from Redis")
        
        # Show a sample file
        if repo_data['files']:
            sample_file = list(repo_data['files'].keys())[0]
            sample_content = repo_data['files'][sample_file]
            print(f"📄 Sample file: {sample_file} ({sample_content['encoding']} encoding)")
        
        print("\n🎉 All tests passed! Pipeline is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False
    
    finally:
        # Cleanup: Remove downloaded files
        if os.path.exists(local_path):
            import shutil
            shutil.rmtree(local_path)
            print(f"🧹 Cleaned up: {local_path}")

def test_quick():
    """Quick test using the integrated function"""
    print("\n🚀 Quick Test: Integrated Download + Storage")
    print("=" * 50)
    
    try:
        storage = RedisRepoStorage()
        success = storage.download_and_store_repo_integrated(
            user_identifier="quicktest@example.com",
            repo_full_name="shivansh-2003/memo",
            local_path="./quick_test_repo"
        )
        
        if success:
            print("✅ Quick test passed!")
            
            # Show what's stored
            repos = storage.get_user_repositories("quicktest@example.com")
            for repo in repos:
                print(f"📦 Stored: {repo['repo_full_name']} - {repo['total_files']} files")
        else:
            print("❌ Quick test failed!")
        
        return success
        
    except Exception as e:
        print(f"❌ Quick test error: {str(e)}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists("./quick_test_repo"):
            import shutil
            shutil.rmtree("./quick_test_repo")

if __name__ == "__main__":
    print("🔬 GitHub -> Redis Pipeline Tests")
    print("Make sure you have GITHUB_ACCESS_TOKEN in your .env file\n")
    
    # Run step-by-step test
    step_by_step_success = test_pipeline()
    
    # Run quick integrated test
    quick_success = test_quick()
    
    print("\n📊 Test Results:")
    print(f"Step-by-step test: {'✅ PASS' if step_by_step_success else '❌ FAIL'}")
    print(f"Quick test: {'✅ PASS' if quick_success else '❌ FAIL'}")
    
    if step_by_step_success and quick_success:
        print("\n🎉 All tests passed! Your pipeline is working perfectly.")
    else:
        print("\n❌ Some tests failed. Check the error messages above.") 