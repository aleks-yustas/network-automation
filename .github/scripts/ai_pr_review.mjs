#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const DEEPSEEK_BASE_URL = process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com";
const DEEPSEEK_MODEL = process.env.DEEPSEEK_MODEL || "deepseek-v4-flash";
const DEEPSEEK_KEY = process.env.DEEPSEEK_KEY || "";
const MAX_FILE_CHARS = 12000;
const MAX_DIFF_CHARS = 26000;

function parseArgs(argv) {
  const result = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      result[key] = true;
      continue;
    }
    result[key] = next;
    i += 1;
  }
  return result;
}

async function readText(filePath, fallback = "") {
  if (!filePath) return fallback;
  return fs.readFile(filePath, "utf8").catch(() => fallback);
}

function truncate(text, maxChars) {
  const normalized = String(text || "");
  if (normalized.length <= maxChars) return normalized;
  return `${normalized.slice(0, maxChars)}\n\n[truncated]`;
}

async function readPrBody(eventPath) {
  const raw = await readText(eventPath, "");
  if (!raw.trim()) return "";
  try {
    const payload = JSON.parse(raw);
    return payload.pull_request?.body || "";
  } catch {
    return raw;
  }
}

async function readChangedFiles(filePath) {
  const raw = await readText(filePath, "");
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

async function safeRead(repoRoot, relativePath) {
  const absolute = path.join(repoRoot, relativePath);
  const content = await fs.readFile(absolute, "utf8").catch(() => null);
  if (content == null) return null;
  return `FILE: ${relativePath}\n${truncate(content, MAX_FILE_CHARS)}`;
}

async function buildContext(repoRoot, changedFiles) {
  const contextFiles = [
    "docs/netops-automation.md",
    "docs/technical-modules.md",
    "docs/modules/README.md",
    "pyproject.toml",
    ...changedFiles.slice(0, 10),
  ];
  const unique = [...new Set(contextFiles)];
  const blocks = [];
  for (const relativePath of unique) {
    const block = await safeRead(repoRoot, relativePath);
    if (block) blocks.push(block);
  }
  return blocks.join("\n\n---\n\n");
}

async function callLlm(messages) {
  if (!DEEPSEEK_KEY) {
    throw new Error("DEEPSEEK_KEY is not configured");
  }
  const response = await fetch(`${DEEPSEEK_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${DEEPSEEK_KEY}`,
    },
    body: JSON.stringify({
      model: DEEPSEEK_MODEL,
      messages,
      stream: false,
      temperature: 0.2,
    }),
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`LLM error ${response.status}: ${body}`.trim());
  }
  const payload = await response.json();
  return payload.choices?.[0]?.message?.content?.trim() || "";
}

async function currentBranch(repoRoot) {
  const { stdout } = await execFileAsync("git", ["branch", "--show-current"], {
    cwd: repoRoot,
  });
  return stdout.trim() || "(detached)";
}

async function gitStatus(repoRoot) {
  const { stdout } = await execFileAsync("git", ["status", "--short"], {
    cwd: repoRoot,
  });
  return stdout.trim();
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const repoRoot = path.resolve(args["repo-root"] || process.cwd());
  const prTitle = args["pr-title"] || "";
  const prNumber = args["pr-number"] || "";
  const diff = truncate(await readText(args["diff-file"], ""), MAX_DIFF_CHARS);
  const changedFiles = await readChangedFiles(args["changed-files-file"]);
  const prBody = await readPrBody(args["pr-body-file"]);
  const branch = await currentBranch(repoRoot);
  const status = await gitStatus(repoRoot);
  const context = await buildContext(repoRoot, changedFiles);

  if (!diff.trim()) {
    throw new Error("Diff is empty");
  }

  const review = await callLlm([
    {
      role: "system",
      content:
        "Ты AI reviewer проекта network-automation.\n" +
        "Проект: offline automation service для сетевого оборудования.\n" +
        "Оцени diff с учетом архитектуры проекта и документации.\n" +
        "Ищи:\n" +
        "1. потенциальные баги\n" +
        "2. архитектурные проблемы\n" +
        "3. рекомендации\n" +
        "Не выдумывай замечания без опоры на diff или контекст.\n" +
        "Отвечай на русском.\n" +
        "Формат строго markdown:\n" +
        "## AI Review\n" +
        "### Summary\n" +
        "...\n\n" +
        "### Потенциальные баги\n" +
        "- ...\n\n" +
        "### Архитектурные проблемы\n" +
        "- ...\n\n" +
        "### Рекомендации\n" +
        "- ...\n\n" +
        "### Основание\n" +
        "- file/path: почему это важно",
    },
    {
      role: "user",
      content:
        `PR #${prNumber}\n` +
        `Title: ${prTitle}\n` +
        `Body:\n${prBody || "(empty)"}\n\n` +
        `Branch: ${branch}\n` +
        `Changed files:\n${changedFiles.join("\n") || "(none)"}\n\n` +
        `Git status:\n${status || "(clean)"}\n\n` +
        `Project context:\n${context}\n\n` +
        `Unified diff:\n${diff}`,
    },
  ]);

  const output = args.output ? path.resolve(args.output) : null;
  const jsonOutput = args["json-output"] ? path.resolve(args["json-output"]) : null;

  if (output) {
    await fs.mkdir(path.dirname(output), { recursive: true });
    await fs.writeFile(output, `${review.trim()}\n`, "utf8");
  }

  if (jsonOutput) {
    await fs.mkdir(path.dirname(jsonOutput), { recursive: true });
    await fs.writeFile(
      jsonOutput,
      JSON.stringify(
        {
          pr_number: prNumber,
          pr_title: prTitle,
          branch,
          changed_files: changedFiles,
          review,
        },
        null,
        2,
      ),
      "utf8",
    );
  }

  process.stdout.write(review);
}

main().catch((error) => {
  console.error(`ai_pr_review error: ${error.message}`);
  process.exit(1);
});
