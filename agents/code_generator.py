from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import Graph, StateGraph, END
from langgraph.prebuilt import ToolExecutor
import os
from dotenv import load_dotenv

# Import existing agents
from code_review import review_code
from bug_agent import find_bugs

load_dotenv()

# State definition for LangGraph
class CodeGeneratorState(TypedDict):
    input_files: Dict[str, str]  # filename -> content
    code_review_results: Dict[str, str]  # filename -> review
    bug_analysis_results: Dict[str, str]  # filename -> bug report
    analysis_summary: str
    chat_history: List[BaseMessage]
    current_query: str
    generated_response: str
    context_ready: bool

class CodeGenerationRequest(BaseModel):
    task_type: str = Field(description="refactor|optimize|debug|extend|create_new|explain|test")
    priority: str = Field(description="high|medium|low")
    requirements: str = Field(description="Specific requirements for code generation")
    considerations: str = Field(description="Important factors based on code analysis")

class CodeGeneratorAgent:
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",  # Claude Sonnet 4
            temperature=0.1,
            max_tokens=4000
        )
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="response"
        )
        
        self.system_prompt = """You are an expert code generation assistant with deep knowledge of software development, algorithms, and best practices.

CONTEXT AWARENESS:
You have been provided with:
1. Original code files that need improvement or extension
2. Detailed code review findings (logic errors, performance issues, security vulnerabilities)
3. Comprehensive bug analysis (runtime errors, memory issues, security flaws)

YOUR ROLE:
- Generate high-quality, production-ready code
- Address identified issues from code review and bug analysis
- Provide secure, efficient, and maintainable solutions
- Explain your reasoning and implementation decisions
- Suggest improvements beyond the immediate request

GENERATION PRINCIPLES:
1. **Security First**: Address all security vulnerabilities identified
2. **Performance Optimized**: Implement efficient algorithms and data structures
3. **Bug-Free**: Avoid patterns that caused issues in the original code
4. **Clean Architecture**: Follow SOLID principles and design patterns
5. **Comprehensive**: Include error handling, input validation, and documentation
6. **Testable**: Write code that's easy to unit test

COMMUNICATION STYLE:
- Be direct and actionable
- Explain trade-offs and design decisions
- Provide complete, runnable code examples
- Include inline comments for complex logic
- Suggest additional improvements or considerations
"""

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """
ANALYSIS CONTEXT:
{analysis_summary}

CODE REVIEW FINDINGS:
{code_reviews}

BUG ANALYSIS RESULTS:
{bug_reports}

ORIGINAL CODE FILES:
{original_files}

CURRENT REQUEST:
{user_query}

Please generate code that addresses the issues found in analysis and fulfills the user's request. 
Prioritize fixing critical bugs and security vulnerabilities while implementing the requested functionality.
"""),
            MessagesPlaceholder(variable_name="chat_history"),
        ])

    def generate_code(self, state: CodeGeneratorState) -> str:
        """Generate code based on analysis and user request"""
        try:
            # Prepare context strings
            analysis_summary = state.get("analysis_summary", "")
            code_reviews = "\n".join([f"File: {name}\n{review}" 
                                    for name, review in state.get("code_review_results", {}).items()])
            bug_reports = "\n".join([f"File: {name}\n{report}" 
                                   for name, report in state.get("bug_analysis_results", {}).items()])
            original_files = "\n".join([f"=== {name} ===\n{content}" 
                                       for name, content in state.get("input_files", {}).items()])

            # Create the prompt
            formatted_prompt = self.prompt_template.format_messages(
                analysis_summary=analysis_summary,
                code_reviews=code_reviews,
                bug_reports=bug_reports,
                original_files=original_files,
                user_query=state["current_query"],
                chat_history=state.get("chat_history", [])
            )
            
            response = self.llm.invoke(formatted_prompt)
            
            # Save to memory
            self.memory.save_context(
                {"input": state["current_query"]},
                {"response": response.content}
            )
            
            return response.content
            
        except Exception as e:
            return f"❌ Error generating code: {str(e)}"

class CodeGeneratorWorkflow:
    def __init__(self):
        self.code_agent = CodeGeneratorAgent()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(CodeGeneratorState)
        
        # Add nodes
        workflow.add_node("analyze_code_quality", self._analyze_code_quality)
        workflow.add_node("detect_bugs", self._detect_bugs)
        workflow.add_node("create_analysis_summary", self._create_analysis_summary)
        workflow.add_node("generate_code_response", self._generate_code_response)
        
        # Define the flow
        workflow.set_entry_point("analyze_code_quality")
        workflow.add_edge("analyze_code_quality", "detect_bugs")
        workflow.add_edge("detect_bugs", "create_analysis_summary")
        workflow.add_edge("create_analysis_summary", "generate_code_response")
        workflow.add_edge("generate_code_response", END)
        
        return workflow.compile()
    
    def _analyze_code_quality(self, state: CodeGeneratorState) -> CodeGeneratorState:
        """Run code review analysis on all input files"""
        code_review_results = {}
        
        for filename, content in state["input_files"].items():
            try:
                review_result = review_code(content)
                code_review_results[filename] = review_result
            except Exception as e:
                code_review_results[filename] = f"Review failed: {str(e)}"
        
        state["code_review_results"] = code_review_results
        return state
    
    def _detect_bugs(self, state: CodeGeneratorState) -> CodeGeneratorState:
        """Run bug detection analysis on all input files"""
        bug_analysis_results = {}
        
        for filename, content in state["input_files"].items():
            try:
                bug_result = find_bugs(content)
                bug_analysis_results[filename] = bug_result
            except Exception as e:
                bug_analysis_results[filename] = f"Bug analysis failed: {str(e)}"
        
        state["bug_analysis_results"] = bug_analysis_results
        return state
    
    def _create_analysis_summary(self, state: CodeGeneratorState) -> CodeGeneratorState:
        """Create a comprehensive analysis summary"""
        summary_parts = []
        
        # Count files analyzed
        file_count = len(state["input_files"])
        summary_parts.append(f"📁 Analyzed {file_count} file(s)")
        
        # Summarize critical issues
        critical_issues = []
        for filename, review in state["code_review_results"].items():
            if "Critical Issues" in review or "🚨" in review:
                critical_issues.append(filename)
        
        if critical_issues:
            summary_parts.append(f"🚨 Critical issues found in: {', '.join(critical_issues)}")
        
        # Summarize bug findings
        high_risk_files = []
        for filename, bugs in state["bug_analysis_results"].items():
            if "high" in bugs.lower() or "critical" in bugs.lower():
                high_risk_files.append(filename)
        
        if high_risk_files:
            summary_parts.append(f"⚠️ High-risk bugs detected in: {', '.join(high_risk_files)}")
        
        if not critical_issues and not high_risk_files:
            summary_parts.append("✅ No critical issues detected in static analysis")
        
        state["analysis_summary"] = "\n".join(summary_parts)
        state["context_ready"] = True
        return state
    
    def _generate_code_response(self, state: CodeGeneratorState) -> CodeGeneratorState:
        """Generate the final code response"""
        response = self.code_agent.generate_code(state)
        state["generated_response"] = response
        return state
    
    def process_files_and_query(self, files: Dict[str, str], query: str, 
                               chat_history: List[BaseMessage] = None) -> str:
        """Process code files and generate response for user query"""
        initial_state = CodeGeneratorState(
            input_files=files,
            code_review_results={},
            bug_analysis_results={},
            analysis_summary="",
            chat_history=chat_history or [],
            current_query=query,
            generated_response="",
            context_ready=False
        )
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        return final_state["generated_response"]

class CodeGeneratorChatbot:
    def __init__(self):
        self.workflow = CodeGeneratorWorkflow()
        self.session_files = {}  # Store files for the session
        self.is_initialized = False
        
    def initialize_with_files(self, files: Dict[str, str]) -> str:
        """Initialize the chatbot with code files"""
        self.session_files = files
        self.is_initialized = True
        
        # Run initial analysis
        analysis_query = "Please analyze the provided code files and give me an overview of their current state, including any issues that need attention."
        
        result = self.workflow.process_files_and_query(
            files=files,
            query=analysis_query,
            chat_history=[]
        )
        
        return f"""🤖 **Code Generator Assistant Initialized**

I've analyzed your code files and I'm ready to help! Here's what I found:

{result}

---

💬 **You can now ask me to:**
- Fix bugs and security vulnerabilities
- Optimize performance bottlenecks  
- Refactor code for better maintainability
- Add new features or functionality
- Explain complex code logic
- Generate tests or documentation
- Create related utility functions

What would you like me to help you with?"""
    
    def chat(self, user_message: str) -> str:
        """Handle ongoing chat conversation"""
        if not self.is_initialized:
            return "❌ Please initialize the chatbot with code files first using `initialize_with_files()`"
        
        # Get chat history from memory
        chat_history = self.workflow.code_agent.memory.chat_memory.messages
        
        # Process the query with context
        response = self.workflow.process_files_and_query(
            files=self.session_files,
            query=user_message,
            chat_history=chat_history
        )
        
        return response
    
    def add_files(self, new_files: Dict[str, str]) -> str:
        """Add new files to the session"""
        self.session_files.update(new_files)
        return f"✅ Added {len(new_files)} new file(s) to the session. The context has been updated."
    
    def list_files(self) -> str:
        """List current files in session"""
        if not self.session_files:
            return "📂 No files loaded in current session."
        
        file_list = "\n".join([f"- {name} ({len(content)} chars)" 
                              for name, content in self.session_files.items()])
        return f"📂 **Current Session Files:**\n{file_list}"
    
    def clear_memory(self) -> str:
        """Clear conversation memory"""
        self.workflow.code_agent.memory.clear()
        return "🧹 Conversation memory cleared."

# Utility functions for easy usage
def load_files_from_paths(file_paths: List[str]) -> Dict[str, str]:
    """Load multiple files from file paths"""
    files = {}
    for path in file_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                filename = os.path.basename(path)
                files[filename] = f.read()
        except Exception as e:
            files[path] = f"Error loading file: {str(e)}"
    return files

def load_file_from_string(filename: str, content: str) -> Dict[str, str]:
    """Create file dict from string content"""
    return {filename: content}

# Example usage
if __name__ == "__main__":
    # Initialize the chatbot
    chatbot = CodeGeneratorChatbot()
    
    # Example: Load files from paths
    # files = load_files_from_paths(["example.py", "utils.py"])
    
    # Example: Load from string content
    sample_code = '''
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)  # Potential division by zero bug!

def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(calculate_average(item))
    return result
'''
    
    files = load_file_from_string("sample.py", sample_code)
    
    # Initialize and start chatting
    print(chatbot.initialize_with_files(files))
    print("\n" + "="*50 + "\n")
    
    # Example chat interactions
    responses = [
        "Fix the division by zero bug in the calculate_average function",
        "Optimize the process_data function for better performance",
        "Add input validation and error handling to both functions"
    ]
    
    for query in responses:
        print(f"👤 User: {query}")
        print(f"🤖 Assistant: {chatbot.chat(query)}")
        print("\n" + "-"*30 + "\n")