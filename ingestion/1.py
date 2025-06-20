#!/usr/bin/env python3
"""
Script to inspect what's stored in Redis Cloud
"""

import redis
import json
from redis_imple import RedisRepoStorage

def inspect_redis_contents():
    """Show all data stored in Redis Cloud"""
    
    print("🔍 Inspecting Redis Cloud Contents")
    print("=" * 50)
    
    try:
        storage = RedisRepoStorage()
        
        # Get all keys in Redis
        all_keys = storage.redis_client.keys("*")
        print(f"📊 Total keys in Redis: {len(all_keys)}")
        
        if not all_keys:
            print("❌ No data found in Redis Cloud")
            return
        
        # Group keys by type
        user_keys = {}
        for key in all_keys:
            if key.startswith("user:"):
                parts = key.split(":")
                if len(parts) >= 2:
                    user_id = parts[1]
                    if user_id not in user_keys:
                        user_keys[user_id] = []
                    user_keys[user_id].append(key)
        
        print(f"\n👥 Found {len(user_keys)} users in Redis:")
        
        for user_id, keys in user_keys.items():
            print(f"\n🔹 User ID: {user_id}")
            print(f"   Keys: {len(keys)}")
            
            # Show key types
            for key in keys:
                key_type = storage.redis_client.type(key)
                if ":repos:list" in key:
                    repos = storage.redis_client.smembers(key)
                    print(f"   📋 {key} ({key_type}) -> {len(repos)} repos: {list(repos)}")
                elif ":metadata" in key:
                    metadata = storage.redis_client.hgetall(key)
                    repo_name = metadata.get('repo_full_name', 'Unknown')
                    files_count = metadata.get('total_files', 'Unknown')
                    print(f"   📝 {key} ({key_type}) -> {repo_name} ({files_count} files)")
                elif ":files" in key:
                    file_count = storage.redis_client.hlen(key)
                    print(f"   📁 {key} ({key_type}) -> {file_count} files stored")
                elif ":structure" in key:
                    structure_count = storage.redis_client.llen(key)
                    print(f"   🌳 {key} ({key_type}) -> {structure_count} items")
                else:
                    print(f"   ❓ {key} ({key_type})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error inspecting Redis: {str(e)}")
        return False

def show_specific_repo_files(user_email="test@example.com", repo_name="shivansh-2003/memo"):
    """Show files from a specific repository"""
    
    print(f"\n📂 Files in Repository: {repo_name}")
    print("=" * 50)
    
    try:
        storage = RedisRepoStorage()
        repo_name_redis = repo_name.replace('/', '_')
        
        # Get repository data
        repo_data = storage.get_repository_files(user_email, repo_name_redis)
        
        if 'error' in repo_data:
            print(f"❌ Error: {repo_data['error']}")
            return
        
        print(f"📊 Repository: {repo_data['metadata']['repo_full_name']}")
        print(f"📅 Downloaded: {repo_data['metadata']['download_timestamp']}")
        print(f"📁 Total files: {len(repo_data['files'])}")
        print(f"💾 Total size: {repo_data['metadata']['total_size_bytes']} bytes")
        
        print(f"\n📋 File List:")
        for file_path, file_data in repo_data['files'].items():
            encoding = file_data['encoding']
            size = file_data['size']
            print(f"  📄 {file_path} ({encoding}, {size} bytes)")
        
        # Show content of a small file as example
        print(f"\n📖 Sample File Content:")
        small_files = [(path, data) for path, data in repo_data['files'].items() 
                      if data['size'] < 500 and data['encoding'] == 'utf-8']
        
        if small_files:
            sample_path, sample_data = small_files[0]
            print(f"📄 File: {sample_path}")
            print(f"🔍 Content preview:")
            content = sample_data['content'][:300]
            print(f"```\n{content}\n{'...' if len(sample_data['content']) > 300 else ''}```")
        
        return True
        
    except Exception as e:
        print(f"❌ Error showing repo files: {str(e)}")
        return False

def show_redis_connection_info():
    """Show Redis Cloud connection details"""
    
    print("☁️ Redis Cloud Connection Info")
    print("=" * 50)
    
    try:
        storage = RedisRepoStorage()
        
        # Get Redis info
        info = storage.redis_client.info()
        
        print(f"🌐 Host: redis-11290.c239.us-east-1-2.ec2.redns.redis-cloud.com")
        print(f"🔌 Port: 11290")
        print(f"👤 Username: default")
        print(f"🔒 Password: [HIDDEN]")
        print(f"📊 Redis Version: {info.get('redis_version', 'Unknown')}")
        print(f"💾 Used Memory: {info.get('used_memory_human', 'Unknown')}")
        print(f"🔑 Total Keys: {info.get('db0', {}).get('keys', 0) if 'db0' in info else 0}")
        
        # Test connection
        pong = storage.redis_client.ping()
        print(f"🏓 Connection Test: {'✅ Connected' if pong else '❌ Failed'}")
        
        print(f"\n🌐 Redis Cloud Dashboard:")
        print(f"   You can view your data at: https://app.redislabs.com/")
        print(f"   Database: database-MC4IJX56")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting Redis info: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Redis Cloud Data Inspector")
    print("Checking what's stored in your Redis Cloud database...\n")
    
    # Show connection info
    show_redis_connection_info()
    
    # Show all contents
    inspect_redis_contents()
    
    # Show specific repo files
    show_specific_repo_files("test@example.com", "shivansh-2003/memo")
    show_specific_repo_files("quicktest@example.com", "shivansh-2003/memo")
    
    print("\n✅ Inspection complete!")