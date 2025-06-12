import requests
import base64
import json
from dotenv import load_dotenv
import os
import base64
from github import Github
load_dotenv()

# Your GitHub personal access token
token = os.getenv("GITHUB_ACCESS_TOKEN")
headers = {"Authorization": f"token {token}"}

def download_repo_contents(repo, local_path="./downloaded_repo"):
    contents = repo.get_contents("")
    
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    
    while contents:
        file_content = contents.pop(0)
        file_path = os.path.join(local_path, file_content.path)
        
        if file_content.type == "dir":
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            contents.extend(repo.get_contents(file_content.path))
        else:
            try:
                # Check if the file has content that can be decoded
                if file_content.encoding == "none":
                    print(f"Skipped: {file_content.path} (no content available)")
                    continue
                elif file_content.encoding == "base64":
                    # Decode base64 content
                    decoded_content = base64.b64decode(file_content.content)
                    with open(file_path, 'wb') as f:
                        f.write(decoded_content)
                    print(f"Downloaded (base64): {file_content.path}")
                else:
                    # Use the built-in decoded_content for other encodings
                    with open(file_path, 'wb') as f:
                        f.write(file_content.decoded_content)
                    print(f"Downloaded: {file_content.path}")
            except Exception as e:
                print(f"Error downloading {file_content.path}: {str(e)}")
                continue

# Usage

# List all repositories you have access to
def list_repos():
    url = "https://api.github.com/user/repos?per_page=100"
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

# Save repository list to JSON file
def save_repos_to_json(filename="repos.json"):
    repos = list_repos()
    if repos:
        # Extract only the full_name from each repository
        repo_names = [repo["full_name"] for repo in repos]
        
        with open(filename, 'w') as f:
            json.dump(repo_names, f, indent=2)
        print(f"Repository names saved to {filename}")
        print(f"Found {len(repo_names)} repositories")
        
        # Print the repository names for preview
        print("Repository names:")
        for name in repo_names:
            print(f"  - {name}")
            
        return repo_names
    else:
        print("Failed to get repository list")
        return None

def main():
    # Create GitHub instance
    g = Github(token)
    
    # Get the repository object
    repo = g.get_repo("shivansh-2003/memo")
    
    # Now call download_repo_contents with the repo object
    download_repo_contents(repo)
    print("Repository download completed!")

if __name__ == "__main__":
    main()

    # Download repository contents