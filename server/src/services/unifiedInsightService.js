const fs = require("fs/promises");
const os = require("os");
const path = require("path");
const { execFile } = require("child_process");
const { promisify } = require("util");

const execFileAsync = promisify(execFile);
const FUSION_SCRIPT = path.resolve(__dirname, "../../../component_2/src/fuse_insights.py");

const generateUnifiedInsight = async (evidence) => {
  const temporaryDirectory = await fs.mkdtemp(path.join(os.tmpdir(), "cse-insight-"));
  const inputPath = path.join(temporaryDirectory, "evidence.json");
  try {
    await fs.writeFile(inputPath, JSON.stringify(evidence), { encoding: "utf8", mode: 0o600 });
    const { stdout } = await execFileAsync(
      process.env.PYTHON_BIN || "python",
      [FUSION_SCRIPT, "--input", inputPath],
      {
        cwd: path.dirname(path.dirname(FUSION_SCRIPT)),
        env: process.env,
        timeout: 3 * 60 * 1000,
        maxBuffer: 4 * 1024 * 1024,
      }
    );
    const output = String(stdout || "").trim().split(/\r?\n/).at(-1);
    return JSON.parse(output);
  } finally {
    await fs.rm(temporaryDirectory, { recursive: true, force: true });
  }
};

module.exports = { generateUnifiedInsight };
