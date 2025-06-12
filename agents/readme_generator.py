import os
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
import glob

load_dotenv()

# Pydantic Models for Structured Output
class Feature(BaseModel):
    """Individual feature of the project"""
    title: str = Field(description="Feature title")
    description: str = Field(description="Detailed feature description")

class TechStackItem(BaseModel):
    """Technology stack item"""
    category: str = Field(description="Category like 'Frontend', 'Backend', 'Database', etc.")
    technologies: List[str] = Field(description="List of technologies in this category")

class InstallationStep(BaseModel):
    """Installation step"""
    step_number: int = Field(description="Step number")
    title: str = Field(description="Step title")
    commands: List[str] = Field(description="Commands to execute")
    description: str = Field(description="Additional description if needed")

class UsageExample(BaseModel):
    """Usage example"""
    title: str = Field(description="Example title")
    description: str = Field(description="What this example does")
    code: str = Field(description="Code example")
    language: str = Field(description="Programming language")

class ProjectStructure(BaseModel):
    """Project structure item"""
    path: str = Field(description="File or directory path")
    description: str = Field(description="Description of what this file/directory contains")

class DeploymentOption(BaseModel):
    """Deployment option and instructions"""
    platform: str = Field(description="Deployment platform (Docker, Heroku, Vercel, etc.)")
    title: str = Field(description="Deployment method title")
    prerequisites: List[str] = Field(description="Prerequisites for this deployment method")
    steps: List[str] = Field(description="Step-by-step deployment instructions")
    environment_notes: str = Field(description="Environment-specific notes")
    config_files: List[str] = Field(description="Required configuration files")

class ArchitectureComponent(BaseModel):
    """Architecture component description"""
    name: str = Field(description="Component name")
    type: str = Field(description="Component type (Frontend, Backend, Database, etc.)")
    description: str = Field(description="What this component does")
    technologies: List[str] = Field(description="Technologies used in this component")
    dependencies: List[str] = Field(description="Other components this depends on")

class ArchitectureOverview(BaseModel):
    """System architecture overview"""
    description: str = Field(description="Overall architecture description")
    components: List[ArchitectureComponent] = Field(description="System components")
    data_flow: List[str] = Field(description="Data flow description steps")
    deployment_architecture: str = Field(description="How components are deployed together")
    ascii_diagram: str = Field(description="Simple ASCII architecture diagram")

class ReadmeContent(BaseModel):
    """Complete README content structure"""
    project_title: str = Field(description="Main project title")
    short_description: str = Field(description="Brief one-line description")
    detailed_description: str = Field(description="Detailed project description")
    features: List[Feature] = Field(description="List of project features")
    tech_stack: List[TechStackItem] = Field(description="Technology stack used")
    architecture_overview: ArchitectureOverview = Field(description="System architecture overview")
    prerequisites: List[str] = Field(description="Prerequisites before installation")
    installation_steps: List[InstallationStep] = Field(description="Step-by-step installation guide")
    usage_examples: List[UsageExample] = Field(description="Usage examples")
    deployment_options: List[DeploymentOption] = Field(description="Deployment guides for different platforms")
    project_structure: List[ProjectStructure] = Field(description="Project structure explanation")
    environment_variables: List[str] = Field(description="Required environment variables")
    api_endpoints: Optional[List[str]] = Field(description="API endpoints if applicable", default=None)
    contributing_guidelines: List[str] = Field(description="How to contribute to the project")
    license_info: str = Field(description="License information")
    author_contact: str = Field(description="Author contact information")
    acknowledgments: List[str] = Field(description="Credits and acknowledgments")

class ReadmeGenerator:
    def __init__(self, openai_api_key: str = None):
        """Initialize the README generator"""
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.llm = ChatOpenAI(
            openai_api_key=self.api_key,
            model="gpt-4",
            temperature=0.3
        )
        
        # Set up the output parser
        self.parser = PydanticOutputParser(pydantic_object=ReadmeContent)
    
    def scan_repository(self, repo_path: str) -> Dict[str, Any]:
        """Scan repository and extract file contents"""
        repo_data = {
            "files": {},
            "structure": [],
            "file_types": set(),
            "total_files": 0,
            "deployment_configs": {},
            "architecture_indicators": {}
        }
        
        # Common file extensions to analyze
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt'}
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'}
        doc_extensions = {'.md', '.txt', '.rst', '.org'}
        
        # Deployment configuration files to detect
        deployment_files = {
            'Dockerfile': 'docker',
            'docker-compose.yml': 'docker-compose',
            'docker-compose.yaml': 'docker-compose',
            'Procfile': 'heroku',
            'vercel.json': 'vercel',
            'netlify.toml': 'netlify',
            '.platform.app.yaml': 'platform.sh',
            'app.yaml': 'gcp',
            'appspec.yml': 'aws-codedeploy',
            'buildspec.yml': 'aws-codebuild',
            'azure-pipelines.yml': 'azure',
            'cloudbuild.yaml': 'gcp-cloudbuild',
            'railway.json': 'railway',
            'render.yaml': 'render'
        }
        
        # Architecture indicator files
        architecture_files = {
            'microservices': ['docker-compose.yml', 'kubernetes/', 'k8s/', 'helm/'],
            'monolith': ['main.py', 'app.py', 'index.js', 'server.js'],
            'frontend': ['package.json', 'src/', 'public/', 'components/', 'pages/'],
            'backend': ['api/', 'routes/', 'models/', 'controllers/', 'services/'],
            'database': ['migrations/', 'schema.sql', 'models.py', 'entity/', 'repositories/'],
            'mobile': ['android/', 'ios/', 'flutter/', 'react-native/', 'xamarin/'],
            'ml': ['models/', 'notebooks/', 'data/', 'train.py', 'predict.py']
        }
        
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common build/cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env', 'build', 'dist']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                file_ext = os.path.splitext(file)[1].lower()
                repo_data["file_types"].add(file_ext)
                repo_data["total_files"] += 1
                
                # Check for deployment configurations
                if file in deployment_files:
                    repo_data["deployment_configs"][deployment_files[file]] = relative_path
                
                # Check for architecture indicators
                for arch_type, indicators in architecture_files.items():
                    for indicator in indicators:
                        if indicator in relative_path.lower() or file.lower() == indicator:
                            if arch_type not in repo_data["architecture_indicators"]:
                                repo_data["architecture_indicators"][arch_type] = []
                            repo_data["architecture_indicators"][arch_type].append(relative_path)
                
                # Read file content for important files
                if (file_ext in code_extensions or 
                    file_ext in config_extensions or 
                    file_ext in doc_extensions or
                    file.lower() in ['readme.md', 'package.json', 'requirements.txt', 'dockerfile', 'makefile'] or
                    file in deployment_files):
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if len(content) < 10000:  # Limit file size to avoid token limits
                                repo_data["files"][relative_path] = {
                                    "content": content,
                                    "size": len(content),
                                    "extension": file_ext
                                }
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                
                repo_data["structure"].append(relative_path)
        
        repo_data["file_types"] = list(repo_data["file_types"])
        return repo_data
    
    def create_analysis_prompt(self, repo_data: Dict[str, Any]) -> str:
        """Create a comprehensive prompt for README generation"""
        
        # Summarize repository structure
        structure_summary = "\n".join(repo_data["structure"][:50])  # Limit to first 50 files
        if len(repo_data["structure"]) > 50:
            structure_summary += f"\n... and {len(repo_data['structure']) - 50} more files"
        
        # Summarize file contents
        files_summary = ""
        for file_path, file_info in list(repo_data["files"].items())[:20]:  # Limit to first 20 files
            files_summary += f"\n--- {file_path} ---\n{file_info['content'][:1000]}\n"
        
        # Deployment configurations summary
        deployment_summary = ""
        if repo_data["deployment_configs"]:
            deployment_summary = "\nDEPLOYMENT CONFIGURATIONS DETECTED:\n"
            for platform, config_file in repo_data["deployment_configs"].items():
                deployment_summary += f"- {platform.upper()}: {config_file}\n"
        
        # Architecture indicators summary
        architecture_summary = ""
        if repo_data["architecture_indicators"]:
            architecture_summary = "\nARCHITECTURE INDICATORS:\n"
            for arch_type, files in repo_data["architecture_indicators"].items():
                architecture_summary += f"- {arch_type.upper()}: {', '.join(files[:3])}\n"
        
        prompt = f"""
Analyze the following repository and generate a comprehensive README.md content.

REPOSITORY STATISTICS:
- Total files: {repo_data['total_files']}
- File types found: {', '.join(repo_data['file_types'])}

PROJECT STRUCTURE:
{structure_summary}

{deployment_summary}

{architecture_summary}

FILE CONTENTS:
{files_summary}

Based on this repository analysis, generate a comprehensive README structure that includes:

1. **Project Title & Description**: Create an engaging title and both short/detailed descriptions
2. **Features**: Identify key features and functionalities from the code
3. **Tech Stack**: Categorize all technologies used (Frontend, Backend, Database, Tools, etc.)
4. **Architecture Overview**: 
   - Analyze the system architecture based on file structure and code
   - Create a simple ASCII diagram showing component relationships
   - Describe data flow between components
   - Explain deployment architecture
5. **Prerequisites**: What users need before installation
6. **Installation Steps**: Detailed step-by-step installation guide
7. **Usage Examples**: Practical code examples showing how to use the project
8. **Deployment Options**: 
   - Generate deployment guides for detected platforms ({', '.join(repo_data['deployment_configs'].keys()) if repo_data['deployment_configs'] else 'Docker, Heroku, etc.'})
   - Include environment-specific steps
   - List required configuration files
9. **Project Structure**: Explain important files and directories
10. **Environment Variables**: List required environment variables from config files
11. **API Endpoints**: If it's a web service, list main endpoints
12. **Contributing Guidelines**: How others can contribute
13. **License & Contact**: License info and author contact
14. **Acknowledgments**: Credits and thanks

Special instructions for new features:

**DEPLOYMENT GUIDE**: 
- Analyze detected deployment configs and generate platform-specific instructions
- Include prerequisites, step-by-step deployment, and environment notes
- Cover multiple deployment scenarios (development, staging, production)

**ARCHITECTURE OVERVIEW**:
- Create a text-based architecture diagram using ASCII characters
- Identify system components (frontend, backend, database, APIs, etc.)
- Describe how components interact and data flows
- Explain the overall system design and patterns used

Make sure to:
- Infer the project purpose from file contents and structure
- Provide programming-language-agnostic installation instructions where possible
- Include realistic code examples based on actual code found
- Be specific about dependencies and requirements
- Make it beginner-friendly but comprehensive
- Generate deployment instructions based on detected configuration files
- Create clear architecture explanations that help developers understand the system

{self.parser.get_format_instructions()}
"""
        return prompt
    
    def generate_readme_content(self, repo_path: str) -> ReadmeContent:
        """Generate README content from repository analysis"""
        print("Scanning repository...")
        repo_data = self.scan_repository(repo_path)
        
        print("Creating analysis prompt...")
        prompt = self.create_analysis_prompt(repo_data)
        
        print("Generating README content with LangChain...")
        
        # Create chat prompt template
        chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are an expert technical writer who creates comprehensive, professional README files for software projects."),
            HumanMessage(content=prompt)
        ])
        
        # Generate content using LangChain
        response = self.llm(chat_prompt.format_messages())
        
        # Parse the response using Pydantic
        try:
            readme_content = self.parser.parse(response.content)
            return readme_content
        except Exception as e:
            print(f"Error parsing response: {e}")
            print("Raw response:", response.content)
            raise
    
    def format_readme_markdown(self, content: ReadmeContent) -> str:
        """Convert ReadmeContent to formatted Markdown"""
        
        markdown = f"""# {content.project_title}

{content.short_description}

## 📖 Description

{content.detailed_description}

## ✨ Features

"""
        
        for feature in content.features:
            markdown += f"- **{feature.title}**: {feature.description}\n"
        
        markdown += "\n## 🛠️ Tech Stack\n\n"
        
        for tech_category in content.tech_stack:
            markdown += f"**{tech_category.category}:**\n"
            for tech in tech_category.technologies:
                markdown += f"- {tech}\n"
            markdown += "\n"
        
        markdown += "## 📋 Prerequisites\n\n"
        for prereq in content.prerequisites:
            markdown += f"- {prereq}\n"
        
        markdown += "\n## 🚀 Installation\n\n"
        for step in content.installation_steps:
            markdown += f"### {step.step_number}. {step.title}\n\n"
            if step.commands:
                markdown += "```bash\n"
                for cmd in step.commands:
                    markdown += f"{cmd}\n"
                markdown += "```\n\n"
            if step.description:
                markdown += f"{step.description}\n\n"
        
        # Deployment Options Section
        if content.deployment_options:
            markdown += "## 🚀 Deployment\n\n"
            
            for deployment in content.deployment_options:
                markdown += f"### {deployment.title}\n\n"
                
                if deployment.prerequisites:
                    markdown += "**Prerequisites:**\n"
                    for prereq in deployment.prerequisites:
                        markdown += f"- {prereq}\n"
                    markdown += "\n"
                
                if deployment.config_files:
                    markdown += "**Required Files:**\n"
                    for config_file in deployment.config_files:
                        markdown += f"- `{config_file}`\n"
                    markdown += "\n"
                
                markdown += "**Steps:**\n"
                for i, step in enumerate(deployment.steps, 1):
                    markdown += f"{i}. {step}\n"
                markdown += "\n"
                
                if deployment.environment_notes:
                    markdown += f"**Environment Notes:** {deployment.environment_notes}\n\n"
                
                markdown += "---\n\n"
        
        markdown += "## 💡 Usage\n\n"
        for example in content.usage_examples:
            markdown += f"### {example.title}\n\n{example.description}\n\n"
            markdown += f"```{example.language}\n{example.code}\n```\n\n"
        
        markdown += "## 📁 Project Structure\n\n"
        markdown += "```\n"
        for item in content.project_structure:
            markdown += f"{item.path}\n"
        markdown += "```\n\n"
        
        for item in content.project_structure:
            markdown += f"- **{item.path}**: {item.description}\n"
        
        if content.environment_variables:
            markdown += "\n## 🔧 Environment Variables\n\n"
            markdown += "Create a `.env` file in the root directory with the following variables:\n\n"
            markdown += "```env\n"
            for env_var in content.environment_variables:
                markdown += f"{env_var}\n"
            markdown += "```\n\n"
        
        if content.api_endpoints:
            markdown += "## 🌐 API Endpoints\n\n"
            for endpoint in content.api_endpoints:
                markdown += f"- {endpoint}\n"
            markdown += "\n"
        
        markdown += "## 🤝 Contributing\n\n"
        for guideline in content.contributing_guidelines:
            markdown += f"- {guideline}\n"
        
        markdown += f"\n## 📄 License\n\n{content.license_info}\n\n"
        markdown += f"## 👤 Author\n\n{content.author_contact}\n\n"
        
        if content.acknowledgments:
            markdown += "## 🙏 Acknowledgments\n\n"
            for ack in content.acknowledgments:
                markdown += f"- {ack}\n"
        
        markdown += "\n---\n\n"
        markdown += "⭐ Don't forget to star this repository if you found it helpful!\n"
        
        return markdown
    
    def generate_readme(self, repo_path: str, output_path: str = "README.md") -> str:
        """Generate complete README file"""
        try:
            print("Starting README generation...")
            content = self.generate_readme_content(repo_path)
            
            print("Formatting markdown...")
            markdown = self.format_readme_markdown(content)
            
            print(f"Writing README to {output_path}...")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            print(f"✅ README generated successfully: {output_path}")
            return markdown
            
        except Exception as e:
            print(f"❌ Error generating README: {e}")
            raise

def main():
    """Main function to run the README generator"""
    
    # Initialize the generator
    try:
        generator = ReadmeGenerator()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your OpenAI API key in the OPENAI_API_KEY environment variable")
        return
    
    # Get repository path from user
    repo_path = input("Enter the path to your repository: ").strip()
    
    if not os.path.exists(repo_path):
        print(f"Error: Repository path '{repo_path}' does not exist")
        return
    
    # Generate README
    try:
        readme_content = generator.generate_readme(repo_path)
        print("\n" + "="*50)
        print("GENERATED README PREVIEW:")
        print("="*50)
        print(readme_content[:1000] + "..." if len(readme_content) > 1000 else readme_content)
        
    except Exception as e:
        print(f"Failed to generate README: {e}")

if __name__ == "__main__":
    main()