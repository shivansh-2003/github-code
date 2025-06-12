from readme_generator import ReadmeGenerator
generator = ReadmeGenerator()
readme1 = generator.generate_readme(
        repo_path="/Users/shivanshmahajan/Desktop/github-code/ingestion/downloaded_repo",
        output_path="./memo_README.md"
    )

print(readme1)