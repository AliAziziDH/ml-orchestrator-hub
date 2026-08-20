with open("tests/test_compaction_and_routing.py", "r") as f:
    content = f.read()

content = content.replace("def write_file():\n        \"\"\"Writes content to a file on disk.\"\"\"\n        pass", "def write_file():\n        \"\"\"Writes content to a file on disk.\"\"\"")
content = content.replace("def read_file():\n        \"\"\"Reads content from a file.\"\"\"\n        pass", "def read_file():\n        \"\"\"Reads content from a file.\"\"\"")
content = content.replace("def execute_sql():\n        \"\"\"Executes a SQL query against the database.\"\"\"\n        pass", "def execute_sql():\n        \"\"\"Executes a SQL query against the database.\"\"\"")

with open("tests/test_compaction_and_routing.py", "w") as f:
    f.write(content)
