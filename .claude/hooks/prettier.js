// PostToolUse hook: format the file that Edit/Write just touched.
// Claude Code passes the tool input as JSON on stdin (there is no CLAUDE_FILE_PATH env var).
const { spawnSync } = require("child_process");
const path = require("path");

let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  try {
    const filePath = JSON.parse(input).tool_input?.file_path;
    if (!filePath) return;
    // Run from client/ so the locally installed prettier (and any config there) is used.
    // Unsupported file types (e.g. .py) make prettier exit non-zero, which we ignore.
    spawnSync(`npx prettier --write "${path.resolve(filePath)}"`, {
      cwd: path.join(__dirname, "..", "..", "client"),
      stdio: "ignore",
      shell: true,
    });
  } catch {
    // Never block the edit because formatting failed.
  }
});
