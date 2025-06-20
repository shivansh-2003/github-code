import redis
import json
import base64
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from github import Github
from dotenv import load_dotenv
import hashlib
# Import ingestion functionality  
from ingestion import download_repo_contents, list_repos, save_repos_to_json

load_dotenv()

class RedisRepoStorage:
    """
    Redis-based repository storage system for GitHub repositories.
    
    Key Pattern Structure:
    - user:{user_id}:repos:list -> Set of repository names for this user
    - user:{user_id}:repo:{repo_name}:files -> Hash of file paths and contents
    - user:{user_id}:repo:{repo_name}:metadata -> Hash of repository metadata
    - user:{user_id}:repo:{repo_name}:structure -> List of directory structure
    """
    
    def __init__(self, redis_host='redis-11290.c239.us-east-1-2.ec2.redns.redis-cloud.com', 
                 redis_port=11290, redis_db=0, redis_password='H010eGSnpXJnso5GfUxkzvtU9qYZpnnD',
                 redis_username='default'):
        """
        Initialize Redis connection and GitHub client.
        
        Args:
            redis_host: Redis server host (Redis Cloud endpoint)
            redis_port: Redis server port (Redis Cloud port)
            redis_db: Redis database number
            redis_password: Redis password (Redis Cloud password)
            redis_username: Redis username (Redis Cloud username)
        """
        # Initialize Redis connection for Redis Cloud
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            username=redis_username,
            password=redis_password,
            decode_responses=True  # Automatically decode byte responses to strings
        )
        
        # Test Redis connection
        try:
            self.redis_client.ping()
            print("✅ Redis connection established successfully")
        except redis.ConnectionError:
            raise Exception("❌ Failed to connect to Redis server")
        
        # Initialize GitHub client
        github_token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not github_token:
            raise ValueError("❌ GITHUB_ACCESS_TOKEN not found in environment variables")
        
        self.github_client = Github(github_token)
        print("✅ GitHub client initialized successfully")

    def _generate_user_id(self, identifier: str) -> str:
        """
        Generate a consistent user ID from any identifier (email, username, etc.)
        
        Args:
            identifier: User identifier (email, username, etc.)
            
        Returns:
            Hashed user ID for Redis keys
        """
        return hashlib.md5(identifier.encode()).hexdigest()[:12]

    def _get_repo_files_key(self, user_id: str, repo_name: str) -> str:
        """Generate Redis key for repository files"""
        return f"user:{user_id}:repo:{repo_name}:files"
    
    def _get_repo_metadata_key(self, user_id: str, repo_name: str) -> str:
        """Generate Redis key for repository metadata"""
        return f"user:{user_id}:repo:{repo_name}:metadata"
    
    def _get_repo_structure_key(self, user_id: str, repo_name: str) -> str:
        """Generate Redis key for repository structure"""
        return f"user:{user_id}:repo:{repo_name}:structure"
    
    def _get_user_repos_key(self, user_id: str) -> str:
        """Generate Redis key for user's repository list"""
        return f"user:{user_id}:repos:list"

    def _detect_file_encoding(self, file_path: str) -> str:
        """
        Detect if a file is binary or text and return appropriate encoding.
        
        Args:
            file_path: Path to the file
            
        Returns:
            'binary' for binary files, 'utf-8' for text files
        """
        try:
            with open(file_path, 'rb') as f:
                # Read first 1024 bytes to check for binary content
                chunk = f.read(1024)
                
            # Check for null bytes (common in binary files)
            if b'\x00' in chunk:
                return 'binary'
            
            # Try to decode as UTF-8
            try:
                chunk.decode('utf-8')
                return 'utf-8'
            except UnicodeDecodeError:
                return 'binary'
                
        except Exception:
            return 'binary'

    def store_local_repo_to_redis(self, user_identifier: str, repo_full_name: str, 
                                local_repo_path: str = "./downloaded_repo") -> bool:
        """
        Store a locally downloaded repository to Redis.
        This works with repositories downloaded by ingestion.py
        
        Args:
            user_identifier: User identifier (email, username, etc.)
            repo_full_name: Repository name in format 'owner/repo'
            local_repo_path: Path to the locally downloaded repository
            
        Returns:
            True if successful, False otherwise
        """
        user_id = self._generate_user_id(user_identifier)
        repo_name = repo_full_name.replace('/', '_')  # Safe Redis key format
        
        try:
            if not os.path.exists(local_repo_path):
                print(f"❌ Local repository path does not exist: {local_repo_path}")
                return False
            
            print(f"📥 Starting Redis storage of local repository: {repo_full_name}")
            print(f"📁 Local path: {local_repo_path}")
            print(f"👤 User ID: {user_id}")
            
            # Initialize counters
            files_stored = 0
            total_size = 0
            
            # Get Redis keys
            files_key = self._get_repo_files_key(user_id, repo_name)
            metadata_key = self._get_repo_metadata_key(user_id, repo_name)
            structure_key = self._get_repo_structure_key(user_id, repo_name)
            user_repos_key = self._get_user_repos_key(user_id)
            
            # Clear existing data for this repo
            self.redis_client.delete(files_key, metadata_key, structure_key)
            
            # Walk through the local repository
            directory_structure = []
            
            for root, dirs, files in os.walk(local_repo_path):
                # Get relative path from repo root
                rel_root = os.path.relpath(root, local_repo_path)
                if rel_root == '.':
                    rel_root = ''
                
                # Add directories to structure
                for dir_name in dirs:
                    dir_path = os.path.join(rel_root, dir_name) if rel_root else dir_name
                    directory_structure.append({
                        'path': dir_path.replace('\\', '/'),  # Normalize path separators
                        'type': 'dir',
                        'size': 0
                    })
                
                # Process files
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    
                    # Get relative path for Redis storage
                    rel_file_path = os.path.relpath(file_path, local_repo_path)
                    rel_file_path = rel_file_path.replace('\\', '/')  # Normalize path separators
                    
                    try:
                        # Get file size
                        file_size = os.path.getsize(file_path)
                        
                        # Add to directory structure
                        directory_structure.append({
                            'path': rel_file_path,
                            'type': 'file',
                            'size': file_size
                        })
                        
                        # Detect file encoding
                        encoding = self._detect_file_encoding(file_path)
                        
                        if encoding == 'binary':
                            # Read binary file and encode as base64
                            with open(file_path, 'rb') as f:
                                binary_content = f.read()
                            redis_content = base64.b64encode(binary_content).decode('utf-8')
                            content_encoding = 'base64'
                        else:
                            # Read text file
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                redis_content = f.read()
                            content_encoding = 'utf-8'
                        
                        # Create file data
                        file_data = {
                            'content': redis_content,
                            'encoding': content_encoding,
                            'size': len(redis_content),
                            'path': rel_file_path,
                            'original_size': file_size
                        }
                        
                        # Store in Redis
                        self.redis_client.hset(files_key, rel_file_path, json.dumps(file_data))
                        
                        files_stored += 1
                        total_size += len(redis_content)
                        
                        if files_stored % 10 == 0:
                            print(f"📁 Processed {files_stored} files...")
                        
                    except Exception as e:
                        print(f"⚠️  Skipped file {rel_file_path}: {str(e)}")
                        continue
            
            # Store repository metadata
            metadata = {
                'repo_full_name': repo_full_name,
                'repo_description': f'Local repository stored from {local_repo_path}',
                'download_timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'user_identifier': user_identifier,
                'source': 'local_filesystem',
                'local_path': local_repo_path,
                'total_files': files_stored,
                'total_size_bytes': total_size
            }
            
            # Store metadata and structure in Redis
            self.redis_client.hset(metadata_key, mapping=metadata)
            self.redis_client.rpush(structure_key, *[json.dumps(item) for item in directory_structure])
            
            # Add this repository to user's repository list
            self.redis_client.sadd(user_repos_key, repo_name)
            
            # Set expiration for user data (optional - 7 days default)
            expiration_days = 7
            expiration_seconds = expiration_days * 24 * 3600
            self.redis_client.expire(files_key, expiration_seconds)
            self.redis_client.expire(metadata_key, expiration_seconds)
            self.redis_client.expire(structure_key, expiration_seconds)
            self.redis_client.expire(user_repos_key, expiration_seconds)
            
            print(f"✅ Local repository storage completed!")
            print(f"📊 Statistics:")
            print(f"   - Files stored: {files_stored}")
            print(f"   - Total size: {total_size / 1024:.2f} KB")
            print(f"   - Expiration: {expiration_days} days")
            
            return True
            
        except Exception as e:
            print(f"❌ Error storing local repository {repo_full_name}: {str(e)}")
            return False

    def download_and_store_repo_integrated(self, user_identifier: str, repo_full_name: str, 
                                         local_path: str = "./downloaded_repo") -> bool:
        """
        Uses ingestion.py to download repo, then stores it in Redis.
        
        Args:
            user_identifier: User identifier (email, username, etc.)
            repo_full_name: Repository name in format 'owner/repo'
            local_path: Path where to download the repository locally
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"🚀 Downloading {repo_full_name} using ingestion.py...")
            
            # Use ingestion.py functionality to download the repo
            repo = self.github_client.get_repo(repo_full_name)
            download_repo_contents(repo, local_path)
            print("✅ Download completed via ingestion.py")
            
            # Now store the downloaded repo in Redis
            print(f"📥 Storing downloaded repo in Redis...")
            success = self.store_local_repo_to_redis(user_identifier, repo_full_name, local_path)
            
            if success:
                print(f"✅ Repository {repo_full_name} successfully downloaded and stored in Redis!")
            
            return success
            
        except Exception as e:
            print(f"❌ Error in integrated download: {str(e)}")
            return False

    def list_user_repositories(self, user_identifier: str) -> List[str]:
        """
        List all available repositories for the authenticated GitHub user.
        
        Args:
            user_identifier: User identifier (email, username, etc.)
            
        Returns:
            List of repository full names (owner/repo)
        """
        try:
            # Get all repositories accessible to the user
            repos = self.github_client.get_user().get_repos()
            repo_list = [repo.full_name for repo in repos]
            
            print(f"📋 Found {len(repo_list)} repositories for user")
            return repo_list
            
        except Exception as e:
            print(f"❌ Error listing repositories: {str(e)}")
            return []

    def download_repository_to_redis(self, user_identifier: str, repo_full_name: str, 
                                   max_file_size_mb: int = 5) -> bool:
        """
        Download a GitHub repository and store it in Redis for a specific user.
        
        Args:
            user_identifier: User identifier (email, username, etc.)
            repo_full_name: Repository name in format 'owner/repo'
            max_file_size_mb: Maximum file size to store (in MB)
            
        Returns:
            True if successful, False otherwise
        """
        user_id = self._generate_user_id(user_identifier)
        
        try:
            # Get repository object
            repo = self.github_client.get_repo(repo_full_name)
            repo_name = repo_full_name.replace('/', '_')  # Safe Redis key format
            
            print(f"📥 Starting download of repository: {repo_full_name}")
            print(f"👤 User ID: {user_id}")
            
            # Initialize counters and storage
            files_processed = 0
            files_stored = 0
            total_size = 0
            max_size_bytes = max_file_size_mb * 1024 * 1024
            
            # Get Redis keys
            files_key = self._get_repo_files_key(user_id, repo_name)
            metadata_key = self._get_repo_metadata_key(user_id, repo_name)
            structure_key = self._get_repo_structure_key(user_id, repo_name)
            user_repos_key = self._get_user_repos_key(user_id)
            
            # Clear existing data for this repo
            self.redis_client.delete(files_key, metadata_key, structure_key)
            
            # Store repository metadata
            metadata = {
                'repo_full_name': repo_full_name,
                'repo_description': repo.description or '',
                'download_timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'user_identifier': user_identifier,
                'default_branch': repo.default_branch,
                'total_files': 0,  # Will update this later
                'total_size_bytes': 0  # Will update this later
            }
            
            # Get all repository contents recursively
            contents = repo.get_contents("")
            directory_structure = []
            
            while contents:
                file_content = contents.pop(0)
                files_processed += 1
                
                # Add to directory structure
                directory_structure.append({
                    'path': file_content.path,
                    'type': file_content.type,
                    'size': file_content.size if hasattr(file_content, 'size') else 0
                })
                
                if file_content.type == "dir":
                    # Add directory contents to processing queue
                    try:
                        contents.extend(repo.get_contents(file_content.path))
                    except Exception as e:
                        print(f"⚠️  Skipped directory {file_content.path}: {str(e)}")
                        continue
                else:
                    # Process file
                    try:
                        # Skip files that are too large
                        if hasattr(file_content, 'size') and file_content.size > max_size_bytes:
                            print(f"⚠️  Skipped large file: {file_content.path} ({file_content.size} bytes)")
                            continue
                        
                        # Get file content
                        if file_content.encoding == "base64":
                            # Decode base64 content and re-encode for Redis storage
                            decoded_content = base64.b64decode(file_content.content)
                            # Store as base64 string in Redis for binary files
                            redis_content = base64.b64encode(decoded_content).decode('utf-8')
                            content_encoding = 'base64'
                        elif file_content.encoding == "utf-8":
                            # Store text content directly
                            redis_content = file_content.decoded_content.decode('utf-8')
                            content_encoding = 'utf-8'
                        else:
                            # Handle other encodings
                            redis_content = str(file_content.decoded_content)
                            content_encoding = 'decoded'
                        
                        # Store file in Redis hash
                        file_data = {
                            'content': redis_content,
                            'encoding': content_encoding,
                            'size': len(redis_content),
                            'path': file_content.path,
                            'sha': file_content.sha
                        }
                        
                        # Store in Redis
                        self.redis_client.hset(files_key, file_content.path, json.dumps(file_data))
                        
                        files_stored += 1
                        total_size += len(redis_content)
                        
                        if files_stored % 10 == 0:
                            print(f"📁 Processed {files_stored} files...")
                        
                    except Exception as e:
                        print(f"⚠️  Skipped file {file_content.path}: {str(e)}")
                        continue
            
            # Update metadata with final counts
            metadata['total_files'] = files_stored
            metadata['total_size_bytes'] = total_size
            metadata['files_processed'] = files_processed
            
            # Store metadata and structure in Redis
            self.redis_client.hset(metadata_key, mapping=metadata)
            self.redis_client.rpush(structure_key, *[json.dumps(item) for item in directory_structure])
            
            # Add this repository to user's repository list
            self.redis_client.sadd(user_repos_key, repo_name)
            
            # Set expiration for user data (optional - 7 days default)
            expiration_days = 7
            expiration_seconds = expiration_days * 24 * 3600
            self.redis_client.expire(files_key, expiration_seconds)
            self.redis_client.expire(metadata_key, expiration_seconds)
            self.redis_client.expire(structure_key, expiration_seconds)
            self.redis_client.expire(user_repos_key, expiration_seconds)
            
            print(f"✅ Repository download completed!")
            print(f"📊 Statistics:")
            print(f"   - Files processed: {files_processed}")
            print(f"   - Files stored: {files_stored}")
            print(f"   - Total size: {total_size / 1024:.2f} KB")
            print(f"   - Expiration: {expiration_days} days")
            
            return True
            
        except Exception as e:
            print(f"❌ Error downloading repository {repo_full_name}: {str(e)}")
            return False

    def get_user_repositories(self, user_identifier: str) -> List[Dict[str, Any]]:
        """
        Get all repositories stored in Redis for a specific user.
        
        Args:
            user_identifier: User identifier
            
        Returns:
            List of repository information dictionaries
        """
        user_id = self._generate_user_id(user_identifier)
        user_repos_key = self._get_user_repos_key(user_id)
        
        try:
            # Get list of repository names for this user
            repo_names = self.redis_client.smembers(user_repos_key)
            repositories = []
            
            for repo_name in repo_names:
                metadata_key = self._get_repo_metadata_key(user_id, repo_name)
                metadata = self.redis_client.hgetall(metadata_key)
                
                if metadata:
                    # Convert metadata to proper types
                    repo_info = {
                        'repo_name': repo_name,
                        'repo_full_name': metadata.get('repo_full_name', ''),
                        'description': metadata.get('repo_description', ''),
                        'download_timestamp': metadata.get('download_timestamp', ''),
                        'total_files': int(metadata.get('total_files', 0)),
                        'total_size_bytes': int(metadata.get('total_size_bytes', 0)),
                        'default_branch': metadata.get('default_branch', 'main')
                    }
                    repositories.append(repo_info)
            
            return repositories
            
        except Exception as e:
            print(f"❌ Error getting user repositories: {str(e)}")
            return []

    def get_repository_files(self, user_identifier: str, repo_name: str) -> Dict[str, Any]:
        """
        Retrieve all files from a stored repository.
        
        Args:
            user_identifier: User identifier
            repo_name: Repository name (formatted for Redis)
            
        Returns:
            Dictionary containing files and metadata
        """
        user_id = self._generate_user_id(user_identifier)
        
        try:
            files_key = self._get_repo_files_key(user_id, repo_name)
            metadata_key = self._get_repo_metadata_key(user_id, repo_name)
            structure_key = self._get_repo_structure_key(user_id, repo_name)
            
            # Get metadata
            metadata = self.redis_client.hgetall(metadata_key)
            if not metadata:
                return {'error': 'Repository not found'}
            
            # Get all files
            files_data = self.redis_client.hgetall(files_key)
            files = {}
            
            for file_path, file_data_json in files_data.items():
                try:
                    file_data = json.loads(file_data_json)
                    files[file_path] = file_data
                except json.JSONDecodeError:
                    print(f"⚠️  Error decoding file data for: {file_path}")
            
            # Get directory structure
            structure_items = self.redis_client.lrange(structure_key, 0, -1)
            structure = []
            for item in structure_items:
                try:
                    structure.append(json.loads(item))
                except json.JSONDecodeError:
                    continue
            
            return {
                'metadata': metadata,
                'files': files,
                'structure': structure,
                'total_files': len(files)
            }
            
        except Exception as e:
            print(f"❌ Error retrieving repository files: {str(e)}")
            return {'error': str(e)}

    def delete_user_repository(self, user_identifier: str, repo_name: str) -> bool:
        """
        Delete a specific repository for a user.
        
        Args:
            user_identifier: User identifier
            repo_name: Repository name to delete
            
        Returns:
            True if successful, False otherwise
        """
        user_id = self._generate_user_id(user_identifier)
        
        try:
            # Get Redis keys
            files_key = self._get_repo_files_key(user_id, repo_name)
            metadata_key = self._get_repo_metadata_key(user_id, repo_name)
            structure_key = self._get_repo_structure_key(user_id, repo_name)
            user_repos_key = self._get_user_repos_key(user_id)
            
            # Check if repository exists
            if not self.redis_client.exists(metadata_key):
                print(f"⚠️  Repository {repo_name} not found for user")
                return False
            
            # Delete all repository data
            deleted_keys = self.redis_client.delete(files_key, metadata_key, structure_key)
            
            # Remove from user's repository list
            self.redis_client.srem(user_repos_key, repo_name)
            
            print(f"✅ Repository {repo_name} deleted successfully")
            print(f"🗑️  Deleted {deleted_keys} Redis keys")
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting repository {repo_name}: {str(e)}")
            return False

    def delete_all_user_data(self, user_identifier: str) -> bool:
        """
        Delete ALL data for a specific user (all repositories and metadata).
        
        Args:
            user_identifier: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        user_id = self._generate_user_id(user_identifier)
        
        try:
            # Get all repository names for this user
            user_repos_key = self._get_user_repos_key(user_id)
            repo_names = self.redis_client.smembers(user_repos_key)
            
            if not repo_names:
                print(f"ℹ️  No data found for user: {user_identifier}")
                return True
            
            # Delete each repository
            total_deleted_keys = 0
            for repo_name in repo_names:
                files_key = self._get_repo_files_key(user_id, repo_name)
                metadata_key = self._get_repo_metadata_key(user_id, repo_name)
                structure_key = self._get_repo_structure_key(user_id, repo_name)
                
                deleted_count = self.redis_client.delete(files_key, metadata_key, structure_key)
                total_deleted_keys += deleted_count
            
            # Delete user's repository list
            self.redis_client.delete(user_repos_key)
            total_deleted_keys += 1
            
            print(f"✅ All data deleted for user: {user_identifier}")
            print(f"🗑️  Deleted {len(repo_names)} repositories")
            print(f"🗑️  Deleted {total_deleted_keys} Redis keys total")
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting user data: {str(e)}")
            return False

    def get_storage_statistics(self, user_identifier: str = None) -> Dict[str, Any]:
        """
        Get storage statistics for a user or overall system.
        
        Args:
            user_identifier: If provided, get stats for specific user. If None, get system stats.
            
        Returns:
            Dictionary with storage statistics
        """
        try:
            if user_identifier:
                # User-specific statistics
                user_id = self._generate_user_id(user_identifier)
                user_repos_key = self._get_user_repos_key(user_id)
                repo_names = self.redis_client.smembers(user_repos_key)
                
                total_files = 0
                total_size = 0
                repos_info = []
                
                for repo_name in repo_names:
                    metadata_key = self._get_repo_metadata_key(user_id, repo_name)
                    metadata = self.redis_client.hgetall(metadata_key)
                    
                    if metadata:
                        repo_files = int(metadata.get('total_files', 0))
                        repo_size = int(metadata.get('total_size_bytes', 0))
                        
                        total_files += repo_files
                        total_size += repo_size
                        
                        repos_info.append({
                            'repo_name': repo_name,
                            'files': repo_files,
                            'size_bytes': repo_size,
                            'size_mb': round(repo_size / (1024 * 1024), 2)
                        })
                
                return {
                    'user_id': user_id,
                    'user_identifier': user_identifier,
                    'total_repositories': len(repo_names),
                    'total_files': total_files,
                    'total_size_bytes': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'repositories': repos_info
                }
            else:
                # System-wide statistics
                all_keys = self.redis_client.keys("user:*")
                user_keys = set()
                
                for key in all_keys:
                    if ':repos:list' in key:
                        user_keys.add(key.split(':')[1])
                
                return {
                    'total_users': len(user_keys),
                    'total_redis_keys': len(all_keys),
                    'redis_memory_usage': self.redis_client.info('memory')
                }
                
        except Exception as e:
            print(f"❌ Error getting storage statistics: {str(e)}")
            return {'error': str(e)}

    def export_repo_from_redis_to_local(self, user_identifier: str, repo_name: str, 
                                      export_path: str = "./exported_repo") -> bool:
        """
        Export a repository stored in Redis back to local filesystem.
        
        Args:
            user_identifier: User identifier
            repo_name: Repository name (Redis formatted)
            export_path: Path where to export the repository
            
        Returns:
            True if successful, False otherwise
        """
        user_id = self._generate_user_id(user_identifier)
        
        try:
            # Get repository data from Redis
            repo_data = self.get_repository_files(user_identifier, repo_name)
            
            if 'error' in repo_data:
                print(f"❌ Repository not found in Redis: {repo_name}")
                return False
            
            print(f"📤 Exporting repository {repo_name} to local filesystem")
            print(f"📁 Export path: {export_path}")
            
            # Create export directory
            if not os.path.exists(export_path):
                os.makedirs(export_path)
            
            files_exported = 0
            
            # Export all files
            for file_path, file_data in repo_data['files'].items():
                try:
                    # Create local file path
                    local_file_path = os.path.join(export_path, file_path)
                    
                    # Create directory if needed
                    local_dir = os.path.dirname(local_file_path)
                    if local_dir and not os.path.exists(local_dir):
                        os.makedirs(local_dir)
                    
                    # Write file content based on encoding
                    if file_data['encoding'] == 'base64':
                        # Decode base64 and write binary
                        decoded_content = base64.b64decode(file_data['content'])
                        with open(local_file_path, 'wb') as f:
                            f.write(decoded_content)
                    else:
                        # Write text content
                        with open(local_file_path, 'w', encoding='utf-8') as f:
                            f.write(file_data['content'])
                    
                    files_exported += 1
                    
                    if files_exported % 10 == 0:
                        print(f"📁 Exported {files_exported} files...")
                    
                except Exception as e:
                    print(f"⚠️  Error exporting file {file_path}: {str(e)}")
                    continue
            
            print(f"✅ Export completed!")
            print(f"📊 Statistics:")
            print(f"   - Files exported: {files_exported}")
            print(f"   - Export path: {export_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error exporting repository: {str(e)}")
            return False


# Core functionality - simplified and focused (Redis Cloud)
def download_and_store_from_ingestion(user_email: str = "user@example.com", 
                                    repo_name: str = "shivansh-2003/memo"):
    """
    Main function: Download repo using ingestion.py and store in Redis Cloud.
    """
    storage = RedisRepoStorage()  # Uses Redis Cloud by default
    
    print(f"🚀 Starting download and Redis Cloud storage for {repo_name}")
    print(f"☁️  Using Redis Cloud database: database-MC4IJX56")
    
    # Use integrated download (ingestion.py + Redis Cloud storage)
    success = storage.download_and_store_repo_integrated(
        user_identifier=user_email,
        repo_full_name=repo_name,
        local_path="./downloaded_repo"
    )
    
    if success:
        # Show what's stored
        repos = storage.get_user_repositories(user_email)
        for repo in repos:
            if repo['repo_full_name'] == repo_name:
                print(f"📊 Stored in Redis Cloud: {repo['total_files']} files, {repo['total_size_bytes']} bytes")
    
    return success

def store_existing_download(user_email: str = "user@example.com", 
                          repo_name: str = "shivansh-2003/memo"):
    """
    Store a repository that was already downloaded by ingestion.py to Redis Cloud
    """
    storage = RedisRepoStorage()  # Uses Redis Cloud by default
    
    print(f"☁️  Storing to Redis Cloud database: database-MC4IJX56")
    return storage.store_local_repo_to_redis(
        user_identifier=user_email,
        repo_full_name=repo_name,
        local_repo_path="./downloaded_repo"
    )

def get_user_repos(user_email: str = "user@example.com"):
    """
    Get all repositories stored for a user from Redis Cloud
    """
    storage = RedisRepoStorage()  # Uses Redis Cloud by default
    return storage.get_user_repositories(user_email)

def example_usage():
    """Simple example showing core functionality with Redis Cloud"""
    user_email = "user@example.com"
    repo_name = "shivansh-2003/memo"
    
    print("📋 Core Redis Cloud Integration with ingestion.py\n")
    print("☁️  Connected to Redis Cloud database: database-MC4IJX56")
    print("🌐 Endpoint: redis-11290.c239.us-east-1-2.ec2.redns.redis-cloud.com:11290\n")
    
    # Main functionality: Download and store in Redis Cloud
    success = download_and_store_from_ingestion(user_email, repo_name)
    
    if success:
        # List what we have stored in Redis Cloud
        print("\n📚 Repositories stored in Redis Cloud:")
        repos = get_user_repos(user_email)
        for repo in repos:
            print(f"  - {repo['repo_full_name']} ({repo['total_files']} files)")
    
    return success


if __name__ == "__main__":
    example_usage()