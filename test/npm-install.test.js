import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import {
  PACKAGE_ROOT,
  SKILL_FILES,
  getInstallTarget,
  installSkill,
} from "../bin/cli.js";

test("resolves the Codex installation path", () => {
  assert.equal(
    getInstallTarget({
      env: { CODEX_HOME: "C:/codex-home" },
      home: "C:/ignored-home",
    }),
    join("C:/codex-home", "skills", "linuxdo-post-auditor"),
  );
});

test("copies the skill payload into an explicit target", () => {
  const tempRoot = mkdtempSync(join(tmpdir(), "linuxdo-post-auditor-"));
  const target = join(tempRoot, "skill");
  try {
    const installed = installSkill({ packageRoot: PACKAGE_ROOT, target });
    assert.equal(installed, target);
    for (const relativePath of SKILL_FILES) {
      assert.equal(existsSync(join(target, relativePath)), true);
    }
    assert.match(
      readFileSync(join(target, "SKILL.md"), "utf8"),
      /name: linuxdo-post-auditor/,
    );
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
