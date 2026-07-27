#!/usr/bin/env node

import { cpSync, existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const SKILL_NAME = "linuxdo-post-auditor";
export const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const SKILL_FILES = ["SKILL.md", "agents", "references", "scripts"];

export function getCodexHome(env = process.env, home = homedir()) {
  return env.CODEX_HOME || join(home, ".codex");
}

export function getInstallTarget({
  env = process.env,
  home = homedir(),
  directTarget = "",
} = {}) {
  return directTarget
    ? resolve(directTarget)
    : join(getCodexHome(env, home), "skills", SKILL_NAME);
}

export function installSkill({
  packageRoot = PACKAGE_ROOT,
  target = getInstallTarget(),
  force = false,
} = {}) {
  if (existsSync(target)) {
    if (!force) {
      throw new Error(
        `Target already exists: ${target}. Re-run with --force to replace it.`,
      );
    }
    rmSync(target, { recursive: true, force: true });
  }

  mkdirSync(target, { recursive: true });
  for (const relativePath of SKILL_FILES) {
    cpSync(join(packageRoot, relativePath), join(target, relativePath), {
      recursive: true,
      force: true,
    });
  }
  return target;
}

function printHelp() {
  console.log(`Linux DO Post Auditor installer

Usage:
  linuxdo-post-auditor install [--force] [--target <skill-directory>]
  linuxdo-post-auditor path

Commands:
  install   Copy the Codex Skill into <CODEX_HOME>/skills/${SKILL_NAME}
  path      Print the default installation path

Options:
  --force   Replace an existing installation
  --target  Install into an explicit skill directory
  --help    Show this help
`);
}

function readOption(args, option) {
  const index = args.indexOf(option);
  if (index === -1) return "";
  return args[index + 1] || "";
}

export function main(argv = process.argv.slice(2)) {
  const [command = "help", ...args] = argv;
  if (command === "help" || command === "--help" || args.includes("--help")) {
    printHelp();
    return 0;
  }

  if (command === "path") {
    console.log(getInstallTarget());
    return 0;
  }

  if (command !== "install") {
    console.error(`Unknown command: ${command}`);
    printHelp();
    return 2;
  }

  try {
    const target = installSkill({
      target: getInstallTarget({ directTarget: readOption(args, "--target") }),
      force: args.includes("--force"),
    });
    console.log(`Installed ${SKILL_NAME} to ${target}`);
    return 0;
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    return 2;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main();
}
