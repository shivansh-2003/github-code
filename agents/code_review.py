from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
import os 
load_dotenv()

class CodeIssue(BaseModel):
    severity: str = Field(description="critical|high|medium")
    location: str = Field(description="Function/class/line where issue exists")
    problem: str = Field(description="What's wrong")
    solution: str = Field(description="How to fix it")
    impact: str = Field(description="Why this matters for the developer")

class Optimization(BaseModel):
    type: str = Field(description="performance|memory|algorithm|design")
    current_approach: str = Field(description="What the code currently does")
    better_approach: str = Field(description="Improved implementation")
    benefit: str = Field(description="Performance/maintainability gain")

class CodeReview(BaseModel):
    language: str = Field(description="Programming language detected")
    intent: str = Field(description="What this code is trying to accomplish")
    issues: List[CodeIssue] = Field(description="Problems that need fixing")
    optimizations: List[Optimization] = Field(description="Performance and design improvements")
    key_insights: List[str] = Field(description="Important observations about code logic and design")

class TechnicalReviewer:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=CodeReview)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior developer doing code review. Focus ONLY on actionable insights that help developers improve their code.

WHAT TO ANALYZE:
1. Logic errors and bugs
2. Performance bottlenecks 
3. Security vulnerabilities
4. Design flaws that hurt maintainability
5. Algorithm inefficiencies
6. Code intent and clarity

WHAT TO IGNORE:
- Minor style preferences
- Verbose descriptions of what code does
- Academic concepts that don't improve the code
- Overly detailed explanations
- Analysis that doesn't lead to actionable changes

BE PRACTICAL: Every insight should help the developer write better code."""),
            
            ("human", """Review this code and provide only substantial, actionable feedback:

```
{code}
```

Focus on:
- Critical bugs or logic errors
- Performance improvements with clear impact
- Security issues
- Design improvements that make code more maintainable
- Algorithm optimizations
- Code intent and what it's trying to accomplish

Skip minor issues. Only mention problems worth fixing and optimizations worth implementing.

{format_instructions}""")
        ])

    def analyze(self, code: str) -> CodeReview:
        try:
            response = self.llm.invoke(
                self.prompt.format_messages(
                    code=code,
                    format_instructions=self.parser.get_format_instructions()
                )
            )
            return self.parser.parse(response.content)
        except Exception as e:
            return CodeReview(
                language="unknown",
                intent="Analysis failed - code may have syntax errors",
                issues=[CodeIssue(
                    severity="critical",
                    location="Parser",
                    problem=f"Could not analyze code: {str(e)}",
                    solution="Fix syntax errors and retry",
                    impact="Code analysis required for review"
                )],
                optimizations=[],
                key_insights=["Manual code review needed due to parsing failure"]
            )

    def generate_report(self, review: CodeReview) -> str:
        """Generate focused, actionable report"""
        if not review.issues and not review.optimizations and not review.key_insights:
            return f"## Code Review: {review.language}\n\n**Intent:** {review.intent}\n\n✅ **No significant issues found** - Code appears well-structured and efficient."

        lines = [
            f"## Code Review: {review.language}",
            f"**Intent:** {review.intent}",
            ""
        ]

        # Critical Issues First
        critical_issues = [i for i in review.issues if i.severity == "critical"]
        if critical_issues:
            lines.extend(["### 🚨 Critical Issues", ""])
            for issue in critical_issues:
                lines.extend([
                    f"**{issue.location}**",
                    f"Problem: {issue.problem}",
                    f"Fix: {issue.solution}",
                    f"Impact: {issue.impact}",
                    ""
                ])

        # High Priority Issues
        high_issues = [i for i in review.issues if i.severity == "high"]
        if high_issues:
            lines.extend(["### ⚠️ Important Issues", ""])
            for issue in high_issues:
                lines.extend([
                    f"**{issue.location}**",
                    f"Problem: {issue.problem}",
                    f"Fix: {issue.solution}",
                    f"Impact: {issue.impact}",
                    ""
                ])

        # Performance Optimizations
        perf_opts = [o for o in review.optimizations if o.type == "performance"]
        if perf_opts:
            lines.extend(["### ⚡ Performance Improvements", ""])
            for opt in perf_opts:
                lines.extend([
                    f"**Current:** {opt.current_approach}",
                    f"**Better:** {opt.better_approach}",
                    f"**Benefit:** {opt.benefit}",
                    ""
                ])

        # Algorithm Optimizations
        algo_opts = [o for o in review.optimizations if o.type == "algorithm"]
        if algo_opts:
            lines.extend(["### 🔄 Algorithm Improvements", ""])
            for opt in algo_opts:
                lines.extend([
                    f"**Current:** {opt.current_approach}",
                    f"**Better:** {opt.better_approach}",
                    f"**Benefit:** {opt.benefit}",
                    ""
                ])

        # Design Improvements
        design_opts = [o for o in review.optimizations if o.type == "design"]
        if design_opts:
            lines.extend(["### 🏗️ Design Improvements", ""])
            for opt in design_opts:
                lines.extend([
                    f"**Current:** {opt.current_approach}",
                    f"**Better:** {opt.better_approach}",
                    f"**Benefit:** {opt.benefit}",
                    ""
                ])

        # Key Insights
        if review.key_insights:
            lines.extend(["### 💡 Key Insights", ""])
            lines.extend([f"- {insight}" for insight in review.key_insights])

        # Medium Priority Issues (only if space allows)
        medium_issues = [i for i in review.issues if i.severity == "medium"]
        if medium_issues and len(lines) < 50:  # Only show if report isn't too long
            lines.extend(["", "### 📝 Additional Issues", ""])
            for issue in medium_issues:
                lines.extend([
                    f"**{issue.location}:** {issue.problem}",
                    f"Fix: {issue.solution}",
                    ""
                ])

        return "\n".join(lines)

def review_code(code_content: str) -> str:
    """Get focused, actionable code review"""
    reviewer = TechnicalReviewer()
    review = reviewer.analyze(code_content)
    return reviewer.generate_report(review)

def review_file(file_path: str) -> str:
    """Review code from a file path"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            code_content = file.read()
        return review_code(code_content)
    except FileNotFoundError:
        return f"❌ Error: File '{file_path}' not found."
    except UnicodeDecodeError:
        return f"❌ Error: Cannot read file '{file_path}' - unsupported encoding."
    except Exception as e:
        return f"❌ Error: {str(e)}"
