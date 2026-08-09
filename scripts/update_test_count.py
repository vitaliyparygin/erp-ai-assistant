python
import re
import subprocess
from pathlib import Path

README = Path("README.md")

result = subprocess.run(
    ["pytest", "--collect-only", "-q"],
    capture_output=True,
    text=True,
    check=True,
)

match = re.search(r"(\d+) tests? collected", result.stdout)

if not match:
    raise RuntimeError("Could not determine test count")

count = match.group(1)

text = README.read_text()

pattern = r"(<!-- TEST_COUNT -->)\d+(<!-- TEST_COUNT_END -->)"

updated, replacements = re.subn(
    pattern,
    rf"\g<1>{count}\g<2>",
    text,
    count=1,
)

if replacements != 1:
    raise RuntimeError("TEST_COUNT markers not found")

README.write_text(updated)

print(f"Updated README test count: {count}")