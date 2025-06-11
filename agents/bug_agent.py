from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional


class Bug(BaseModel):
    line_number: int = Field(description="Line number where bug occurs")
    bug_type: str = Field(description="null_pointer|index_out_of_bounds|memory_leak|race_condition|logic_error|syntax_error|type_mismatch|infinite_loop|resource_leak")
    severity: str = Field(description="critical|high|medium|low")
    description: str = Field(description="What will go wrong during execution")
    error_scenario: str = Field(description="Specific condition that triggers the bug")
    fix_suggestion: str = Field(description="How to prevent this runtime error")


class SecurityVulnerability(BaseModel):
    line_number: int = Field(description="Line number of vulnerability")
    vulnerability_type: str = Field(description="sql_injection|xss|buffer_overflow|path_traversal|code_injection|authentication_bypass")
    risk_level: str = Field(description="critical|high|medium|low")
    exploit_scenario: str = Field(description="How this could be exploited")
    mitigation: str = Field(description="Security fix recommendation")


class BugReport(BaseModel):
    file_analysis: str = Field(description="Overall code purpose and execution flow")
    total_lines: int = Field(description="Number of lines analyzed")
    bugs: List[Bug] = Field(description="Runtime bugs and errors found")
    security_issues: List[SecurityVulnerability] = Field(description="Security vulnerabilities")
    crash_probability: str = Field(description="high|medium|low - likelihood of runtime crashes")


class BugReportingAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=BugReport)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a bug detection specialist. Analyze code for runtime errors that cause crashes, exceptions, or security vulnerabilities.

Focus on identifying:
- Null/undefined pointer dereferences
- Array/buffer overflows and underflows  
- Memory leaks and resource management issues
- Race conditions and concurrency bugs
- Division by zero and arithmetic errors
- Infinite loops and recursion issues
- Type mismatches and casting errors
- File/network I/O failures
- SQL injection and XSS vulnerabilities
- Authentication and authorization flaws

For each bug, specify the EXACT line number and explain what runtime error will occur."""),
            
            ("human", """Analyze this code for runtime bugs and security vulnerabilities:

```
{code}
```

Examine each line for potential execution errors. Report:
1. Line-specific bugs that cause runtime failures
2. Security vulnerabilities with exploitation scenarios  
3. Overall crash probability assessment

{format_instructions}""")
        ])

    def analyze_bugs(self, code: str) -> BugReport:
        try:
            response = self.llm.invoke(
                self.prompt.format_messages(
                    code=code,
                    format_instructions=self.parser.get_format_instructions()
                )
            )
            return self.parser.parse(response.content)
        except Exception as e:
            # Count lines for fallback
            line_count = len(code.split('\n'))
            return BugReport(
                file_analysis="Analysis failed due to parsing error",
                total_lines=line_count,
                bugs=[Bug(
                    line_number=1,
                    bug_type="syntax_error", 
                    severity="high",
                    description="Code analysis failed - potential syntax issues",
                    error_scenario=f"Parser error: {str(e)}",
                    fix_suggestion="Verify code syntax and structure"
                )],
                security_issues=[],
                crash_probability="high"
            )

    def generate_bug_report(self, report: BugReport) -> str:
        lines = [
            "# 🐛 BUG REPORT",
            f"**File Analysis:** {report.file_analysis}",
            f"**Lines Analyzed:** {report.total_lines}",
            f"**Crash Risk:** {report.crash_probability.upper()}\n"
        ]
        
        if report.bugs:
            lines.append("## 🚨 RUNTIME BUGS:")
            for bug in report.bugs:
                lines.extend([
                    f"**Line {bug.line_number} - {bug.bug_type.upper()} [{bug.severity.upper()}]**",
                    f"💥 **Error:** {bug.description}",
                    f"⚠️  **Trigger:** {bug.error_scenario}",
                    f"🔧 **Fix:** {bug.fix_suggestion}\n"
                ])
        
        if report.security_issues:
            lines.append("## 🔒 SECURITY VULNERABILITIES:")
            for vuln in report.security_issues:
                lines.extend([
                    f"**Line {vuln.line_number} - {vuln.vulnerability_type.upper()} [{vuln.risk_level.upper()}]**",
                    f"🎯 **Exploit:** {vuln.exploit_scenario}",
                    f"🛡️  **Fix:** {vuln.mitigation}\n"
                ])
        
        if not report.bugs and not report.security_issues:
            lines.append("✅ **No critical bugs detected in static analysis**")
        
        return "\n".join(lines)


def find_bugs(code_content: str) -> str:
    """Analyze code for runtime bugs and security issues"""
    agent = BugReportingAgent()
    bug_report = agent.analyze_bugs(code_content)
    return agent.generate_bug_report(bug_report)