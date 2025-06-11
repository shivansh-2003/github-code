from bug_agent import find_bugs

# Read your test file
with open("/Users/shivanshmahajan/Desktop/github-code/sample_code/test.java", "r") as f:
    code_content = f.read()

# Analyze for bugs
result = find_bugs(code_content)
print(result)