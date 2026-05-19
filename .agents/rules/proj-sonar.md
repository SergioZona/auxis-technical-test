# SonarQube Code Quality Rules

Agent must write code that passes strict SonarQube quality gates.

1. **No Bugs**: Prevent NullPointerExceptions, out-of-bounds, and logical errors.
2. **Low Complexity**: Avoid deep nesting. Extract complex logic into small, readable helpers.
3. **No Smells**: Remove unused imports, dead code, and magic numbers.
4. **Coverage**: Always generate test cases for new logic.
5. **Security**: Avoid hardcoded credentials, unsafe regex, and injection vectors.

If user asks for code review, check for these SonarQube violations manually.
