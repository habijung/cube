"""Install regression tests using an isolated repository and HOME."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "cube"
        self.home = self.root / "home"
        self.repo.mkdir()
        self.home.mkdir()
        (self.repo / "scripts").mkdir()
        shutil.copyfile(INSTALLER, self.repo / "scripts/install.sh")
        shutil.copyfile(INSTALLER.parent / "pi_packages.py", self.repo / "scripts/pi_packages.py")
        manifest = INSTALLER.parent.parent / "agents/pi/packages.txt"
        target = self.repo / "agents/pi/packages.txt"
        target.parent.mkdir(parents=True)
        shutil.copyfile(manifest, target)
        self.package_sources = [line for line in manifest.read_text().splitlines()
                                if line and not line.startswith("#")]
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.pi_log = self.root / "pi-calls.jsonl"
        fake_pi = self.bin / "pi"
        fake_pi.write_text(f"#!{sys.executable}\n" + '''import json
import os
from pathlib import Path
import sys

command, source = sys.argv[1:]
with open(os.environ["FAKE_PI_LOG"], "a") as log:
    log.write(json.dumps({"args": sys.argv[1:], "cwd": os.getcwd()}) + "\\n")
if os.environ.get("FAKE_PI_FAIL") == source:
    sys.exit(2)
if os.environ.get("FAKE_PI_NOOP"):
    sys.exit(0)
agent = Path(os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi/agent")))
settings = agent / "settings.json"
settings.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(settings.read_text()) if settings.exists() else {}
packages = data.setdefault("packages", [])
if not any((p.get("source") if isinstance(p, dict) else p) == source for p in packages):
    packages.append(source)
settings.write_text(json.dumps(data))
name = source[4:]
package = agent / "npm/node_modules" / name / "package.json"
package.parent.mkdir(parents=True, exist_ok=True)
package.write_text(json.dumps({"name": name, "version": "2.0.0"}))
''')
        fake_pi.chmod(0o755)
        (self.repo / "cube.sh").write_text("# Isolated alias fixture\n")
        self.skills = ("cube-example", "cube-other")
        for name in self.skills:
            source = self.repo / "skills" / name
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("# Fixture\n")
        for relative, content in (
            ("agents/claude/cube-status-line.sh", "#!/usr/bin/env bash\n"),
            ("agents/gemini/policies/cube.toml", "# Fixture policy\n"),
            ("agents/opencode/plugins/cmux-notify.js", "// Fixture plugin\n"),
        ):
            source = self.repo / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(content)
        self.env = dict(os.environ, HOME=str(self.home), SHELL="/bin/zsh")
        for name in ("PI_CODING_AGENT_DIR", "PI_OFFLINE", "FAKE_PI_FAIL", "FAKE_PI_NOOP"):
            self.env.pop(name, None)
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ["PATH"]
        self.env["FAKE_PI_LOG"] = str(self.pi_log)
        self.shell = "bash"

    def install(self, *args):
        env = self.env.copy()
        for name in ("BASH_ENV", "ENV", "ZDOTDIR"):
            env.pop(name, None)
        return subprocess.run(
            [self.shell, "scripts/install.sh", *args], cwd=self.repo,
            env=env, input="", text=True, capture_output=True, timeout=15,
        )

    def successful_install(self, *args):
        result = self.install(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def assert_skills(self, base):
        for name in self.skills:
            link = self.home / base / "skills" / name
            self.assertTrue(link.is_symlink(), str(link))
            self.assertEqual(os.readlink(link), str(self.repo / "skills" / name))

    def prepare_claude(self):
        # The installer expects the Claude CLI to have created its directory.
        directory = self.home / ".claude"
        directory.mkdir(exist_ok=True)
        (directory / "settings.json").write_text("{}\n")

    def legacy_links(self):
        links = {}
        for agent, base in (("gemini", ".gemini"), ("opencode", ".config/opencode")):
            directory = self.home / base / "skills"
            directory.mkdir(parents=True, exist_ok=True)
            link = directory / "cube-example"
            link.symlink_to(self.repo / "skills/cube-example")
            (directory / "unrelated.txt").write_text("Keep this file\n")
            links[agent] = link
        return links

    def check_inherited_startup_isolation(self):
        alternate_home = self.root / "alternate-home"
        alternate_home.mkdir()
        startup_directory = self.root / "startup"
        startup_directory.mkdir()
        sentinel = self.root / "startup-ran"
        startup = startup_directory / ".zshenv"
        startup.write_text(
            f'export HOME="{alternate_home}"\n'
            f'touch "{sentinel}"\n'
        )
        inherited = {
            "BASH_ENV": str(startup),
            "ENV": str(startup),
            "ZDOTDIR": str(startup_directory),
        }
        with patch.dict(os.environ, inherited):
            self.env.update(inherited)
            self.successful_install("pi")
        self.assertFalse(sentinel.exists(), "Inherited startup script was executed")
        self.assertEqual(list(alternate_home.iterdir()), [])
        self.assert_skills(".agents")
        self.assertIn(
            f"source {self.repo}/cube.sh", (self.home / ".zshrc").read_text(),
        )
        for name, value in inherited.items():
            self.assertEqual(self.env[name], value)

    def test_bash_ignores_inherited_startup_configuration(self):
        self.check_inherited_startup_isolation()

    @unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
    def test_zsh_ignores_inherited_startup_configuration(self):
        self.shell = "zsh"
        self.check_inherited_startup_isolation()

    def test_pi_uses_shared_skills_without_agent_specific_directories(self):
        output = self.successful_install("pi")
        self.assert_skills(".agents")
        self.assertIn("[pi]", output)
        self.assertNotIn("Unknown agent", output)
        for relative in (".pi/agent/skills", ".pi/.agents", ".claude", ".gemini", ".config/opencode"):
            self.assertFalse((self.home / relative).exists(), relative)
        rc = (self.home / ".zshrc").read_text()
        self.assertIn(f"source {self.repo}/cube.sh", rc)

    def test_pi_reinstallation_keeps_existing_links_and_alias_registration(self):
        self.successful_install("pi")
        links = [self.home / ".agents/skills" / name for name in self.skills]
        inodes = [link.lstat().st_ino for link in links]
        rc = (self.home / ".zshrc").read_text()
        output = self.successful_install("pi")
        self.assertEqual([link.lstat().st_ino for link in links], inodes)
        self.assertEqual((self.home / ".zshrc").read_text(), rc)
        self.assertEqual(output.count("already symlinked"), len(self.skills))

    def test_pi_reuses_opencode_installation_without_changing_its_plugin(self):
        self.successful_install("opencode")
        skill = self.home / ".agents/skills/cube-example"
        plugin = self.home / ".config/opencode/plugins/cmux-notify.js"
        before = (skill.lstat().st_ino, plugin.lstat().st_ino, os.readlink(plugin))
        self.successful_install("pi")
        self.assertEqual(
            (skill.lstat().st_ino, plugin.lstat().st_ino, os.readlink(plugin)), before,
        )
        self.assert_skills(".agents")
        self.assertTrue((self.home / ".pi/agent/settings.json").is_file())

    def test_opencode_and_pi_share_links_in_either_selection_order(self):
        for agents in (("opencode", "pi"), ("pi", "opencode")):
            with self.subTest(agents=agents):
                self.home = self.root / f"home-{agents[0]}"
                self.home.mkdir()
                self.env["HOME"] = str(self.home)
                output = self.successful_install(*agents)
                self.assert_skills(".agents")
                self.assertIn("[pi]", output)
                self.assertIn("[opencode]", output)
                self.assertTrue((self.home / ".config/opencode/plugins/cmux-notify.js").is_symlink())
                self.assertTrue((self.home / ".pi/agent/settings.json").is_file())

    def test_default_installation_includes_pi_and_existing_agent_resources(self):
        self.prepare_claude()
        output = self.successful_install()
        self.assertIn("Defaulting to: claude, gemini, opencode, pi", output)
        self.assertIn("[pi]", output)
        self.assert_skills(".claude")
        self.assert_skills(".agents")
        self.assertTrue((self.home / ".claude/cube-status-line.sh").is_symlink())
        settings = json.loads((self.home / ".claude/settings.json").read_text())
        self.assertEqual(settings["statusLine"]["type"], "command")
        self.assertTrue((self.home / ".gemini/policies/cube.toml").is_symlink())
        self.assertTrue((self.home / ".config/opencode/plugins/cmux-notify.js").is_symlink())
        self.assertTrue((self.home / ".pi/agent/settings.json").is_file())
        check = self.successful_install("--check")
        self.assertIn("[pi] Skills directory exists:", check)
        self.assertIn("All systems nominal!", check)

    def test_existing_agents_remain_individually_installable(self):
        for agent in ("claude", "gemini", "opencode"):
            with self.subTest(agent=agent):
                self.home = self.root / f"home-{agent}"
                self.home.mkdir()
                self.env["HOME"] = str(self.home)
                if agent == "claude":
                    self.prepare_claude()
                output = self.successful_install(agent)
                self.assert_skills(".claude" if agent == "claude" else ".agents")
                self.assertNotIn("[pi]", output)
                if agent == "claude":
                    self.assertFalse((self.home / ".gemini").exists())
                    self.assertFalse((self.home / ".config/opencode").exists())
                elif agent == "gemini":
                    self.assertTrue((self.home / ".gemini/policies/cube.toml").is_symlink())
                else:
                    self.assertTrue((self.home / ".config/opencode/plugins/cmux-notify.js").is_symlink())

    def test_pi_installation_preserves_both_legacy_agent_skill_paths(self):
        links = self.legacy_links()
        inodes = {agent: link.lstat().st_ino for agent, link in links.items()}
        self.successful_install("pi")
        for agent, link in links.items():
            self.assertTrue(link.is_symlink(), agent)
            self.assertEqual(link.lstat().st_ino, inodes[agent])
            self.assertEqual((link.parent / "unrelated.txt").read_text(), "Keep this file\n")

    def test_legacy_cleanup_only_applies_to_selected_agent(self):
        for selected in ("gemini", "opencode"):
            with self.subTest(selected=selected):
                links = self.legacy_links()
                self.successful_install(selected)
                for agent, link in links.items():
                    self.assertEqual(link.is_symlink(), agent != selected)
                    self.assertTrue((link.parent / "unrelated.txt").is_file())
                # Reset only these fixture links for the next selection.
                for link in links.values():
                    if link.is_symlink():
                        link.unlink()

    def test_default_installation_still_cleans_both_legacy_paths(self):
        self.prepare_claude()
        links = self.legacy_links()
        self.successful_install()
        for link in links.values():
            self.assertFalse(link.is_symlink())
            self.assertTrue((link.parent / "unrelated.txt").is_file())

    def test_diagnostics_show_pi_without_creating_missing_agent_directories(self):
        self.successful_install("pi")
        result = self.install("--check")
        output = result.stdout
        self.assertIn("[pi] Skills directory exists:", output)
        self.assertIn(str(self.home / ".agents/skills"), output)
        pi_section = output.split("[pi] Skills directory exists:", 1)[1]
        for name in self.skills:
            self.assertIn(f"{name}: Symlinked correctly", pi_section)
        # --check remains a full-environment diagnostic; Gemini policy is absent.
        self.assertGreater(result.returncode, 0)
        self.assertNotIn("All systems nominal!", output)
        for relative in (".claude", ".gemini", ".config/opencode"):
            self.assertFalse((self.home / relative).exists(), relative)

    def test_diagnostics_report_broken_shared_link_for_pi(self):
        self.prepare_claude()
        self.successful_install()
        link = self.home / ".agents/skills/cube-example"
        link.unlink()
        link.symlink_to(self.root / "missing-skill")
        result = self.install("--check")
        self.assertGreater(result.returncode, 0)
        self.assertIn("[pi] Skills directory exists:", result.stdout)
        pi_section = result.stdout.split("[pi] Skills directory exists:", 1)[1]
        self.assertIn("cube-example: Broken or missing link", pi_section)
        self.assertIn("gemini opencode pi", result.stdout)

    def test_pi_preserves_existing_agent_settings_and_resources(self):
        originals = {
            ".pi/agent/settings.json": '{"theme": "dark"}\n',
            ".claude/settings.json": '{"custom": true}\n',
            ".gemini/settings.json": '{"custom": true}\n',
            ".gemini/policies/custom.toml": "# User policy\n",
            ".config/opencode/plugins/custom.js": "// User plugin\n",
        }
        for relative, content in originals.items():
            path = self.home / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.successful_install("pi")
        for relative, content in originals.items():
            if relative == ".pi/agent/settings.json":
                settings = json.loads((self.home / relative).read_text())
                self.assertEqual(settings["theme"], "dark")
                self.assertEqual(settings["packages"], self.package_sources)
            else:
                self.assertEqual((self.home / relative).read_text(), content)
        self.assertEqual(list((self.home / ".pi").iterdir()), [self.home / ".pi/agent"])
        self.assertFalse((self.home / ".pi/agent/skills").exists())
        self.assertFalse((self.home / ".pi/.agents").exists())

    def test_claude_installation_preserves_legacy_shared_agent_links(self):
        links = self.legacy_links()
        self.prepare_claude()
        self.successful_install("claude")
        for link in links.values():
            self.assertTrue(link.is_symlink())

    @unittest.skipUnless(shutil.which("zsh"), "zsh is not installed")
    def test_pi_and_default_installation_also_work_with_zsh(self):
        self.shell = "zsh"
        self.successful_install("pi")
        self.assert_skills(".agents")
        self.assertTrue((self.home / ".pi/agent/settings.json").is_file())
        self.prepare_claude()
        self.successful_install()
        check = self.successful_install("--check")
        self.assertIn("[pi] Skills directory exists:", check)
        self.assertIn("All systems nominal!", check)

    def test_selected_legacy_directory_is_removed_only_when_empty(self):
        directory = self.home / ".gemini/skills"
        directory.mkdir(parents=True)
        (directory / "cube-example").symlink_to(self.repo / "skills/cube-example")
        self.successful_install("gemini")
        self.assertFalse(directory.exists())
        self.assert_skills(".agents")

    def pi_calls(self):
        if not self.pi_log.exists():
            return []
        return [json.loads(line) for line in self.pi_log.read_text().splitlines()]

    def pi_settings(self, value):
        path = self.home / ".pi/agent/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def test_pi_installs_then_updates_only_managed_packages(self):
        self.pi_settings({"packages": ["npm:user-package"], "theme": "custom"})
        self.successful_install("pi")
        self.successful_install("pi")
        calls = self.pi_calls()
        self.assertEqual([call["args"] for call in calls],
                         [["install", source] for source in self.package_sources] +
                         [["update", source] for source in self.package_sources])
        for call in calls:
            self.assertNotEqual(Path(call["cwd"]), self.repo)
            self.assertFalse(Path(call["cwd"]).exists())
        settings = json.loads((self.home / ".pi/agent/settings.json").read_text())
        self.assertEqual(settings["theme"], "custom")
        self.assertIn("npm:user-package", settings["packages"])

    def test_other_agent_selection_does_not_call_pi(self):
        self.successful_install("opencode")
        self.assertEqual(self.pi_calls(), [])
        self.assertFalse((self.home / ".pi").exists())

    def test_check_is_read_only_and_does_not_invoke_pi(self):
        self.prepare_claude()
        self.successful_install()
        before = {str(p): p.read_bytes() for p in self.home.rglob("*")
                  if p.is_file() and not p.is_symlink()}
        calls = self.pi_calls()
        output = self.successful_install("--check")
        self.assertIn("installed 2.0.0 (local files only)", output)
        self.assertIn("extension loading are not checked", output)
        self.assertEqual(self.pi_calls(), calls)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.home.rglob("*")
                                 if p.is_file() and not p.is_symlink()})

    def test_pi_repairs_missing_managed_installation_and_keeps_filters(self):
        source = self.package_sources[0]
        entry = {"source": source, "extensions": [], "skills": ["custom"]}
        path = self.pi_settings({"packages": [entry]})
        self.successful_install("pi")
        self.assertEqual(self.pi_calls()[0]["args"], ["install", source])
        self.assertEqual(json.loads(path.read_text())["packages"][0], entry)
        self.successful_install("pi")
        self.assertEqual(json.loads(path.read_text())["packages"][0], entry)

    def test_pi_preserves_and_reports_version_constraints_and_duplicates(self):
        source = self.package_sources[0]
        for entries in ([source + "@1.0.0"], [source, source],
                        [{"source": source + "@latest", "extensions": []}]):
            with self.subTest(entries=entries):
                path = self.pi_settings({"packages": entries})
                result = self.install("pi")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("preserved, skipped", result.stdout)
                self.assertEqual(json.loads(path.read_text())["packages"][:len(entries)], entries)
                self.assertFalse(any(call["args"][1] == source for call in self.pi_calls()))
                self.assertNotIn("Setup complete!", result.stdout)

    def test_invalid_settings_stop_before_any_installation(self):
        for value in ([], {"packages": {}}, {"packages": [None]}, {"packages": [{"source": 1}]}):
            with self.subTest(value=value):
                path = self.pi_settings(value)
                before = path.read_bytes()
                result = self.install("pi")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(self.pi_calls(), [])
                self.assertFalse((self.home / ".zshrc").exists())
        path.write_text("{invalid json")
        self.assertNotEqual(self.install("pi").returncode, 0)
        self.assertEqual(path.read_text(), "{invalid json")

    def test_invalid_manifest_stops_before_any_installation(self):
        path = self.repo / "agents/pi/packages.txt"
        for content in ("", "npm:pi-tools@latest\n", "$(touch injected)\n",
                        "npm:pi-tools\nnpm:pi-tools\n", "npm:../escape\n"):
            with self.subTest(content=content):
                path.write_text(content)
                self.assertNotEqual(self.install("pi").returncode, 0)
                self.assertEqual(self.pi_calls(), [])
                self.assertFalse((self.home / ".zshrc").exists())

    def test_package_failure_reports_partial_success_and_retry_recovers(self):
        source = self.package_sources[0]
        self.env["FAKE_PI_FAIL"] = source
        result = self.install("pi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exit 2", result.stdout)
        self.assertIn("Setup incomplete", result.stdout)
        self.assertEqual(len(self.pi_calls()), len(self.package_sources))
        self.env.pop("FAKE_PI_FAIL")
        self.successful_install("pi")

    def test_success_exit_without_installed_files_is_not_success(self):
        self.env["FAKE_PI_NOOP"] = "1"
        result = self.install("pi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installation verification failed", result.stdout)
        self.assertNotIn("Setup complete!", result.stdout)

    def test_corrupt_package_metadata_is_reported_and_repaired(self):
        self.successful_install("pi")
        source = self.package_sources[0]
        path = self.home / ".pi/agent/npm/node_modules" / source[4:] / "package.json"
        for content in ("{invalid", "[]", '{"name": "wrong", "version": "1.0.0"}'):
            with self.subTest(content=content):
                path.write_text(content)
                result = self.install("--check")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("managed installation missing or invalid", result.stdout)
                self.successful_install("pi")
                self.assertIn(["install", source], [call["args"] for call in self.pi_calls()[-2:]])

    def test_offline_install_fails_without_modification(self):
        self.env["PI_OFFLINE"] = "true"
        result = self.install("pi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PI_OFFLINE", result.stdout)
        self.assertEqual(self.pi_calls(), [])
        self.assertFalse((self.home / ".zshrc").exists())

    def test_pi_missing_cli_is_not_auto_installed(self):
        (self.bin / "pi").unlink()
        for name in ("bash", "basename", "python3"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.env["PATH"] = str(self.bin)
        result = self.install("pi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CLI not found", result.stdout)
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertEqual(self.pi_calls(), [])

    def test_missing_python_is_reported_before_modification(self):
        # A minimal PATH prevents fallback to the real host's Python or Pi.
        for name in ("bash", "basename"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.env["PATH"] = str(self.bin)
        result = self.install("pi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("python3 is required", result.stdout)
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertEqual(self.pi_calls(), [])

    def test_pi_honors_agent_directory_override_without_touching_default(self):
        self.env["PI_CODING_AGENT_DIR"] = "custom-pi"
        self.successful_install("pi")
        self.assertTrue((self.repo / "custom-pi/settings.json").is_file())
        self.assertFalse((self.home / ".pi").exists())
        # Resolve the relative override from the repository, not the neutral cwd.
        result = self.install("--check")
        self.assertIn("installed 2.0.0", result.stdout)

    def test_check_reports_missing_registration_and_installation(self):
        self.pi_settings({"packages": [self.package_sources[0]]})
        result = self.install("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("managed installation missing or invalid", result.stdout)
        self.assertIn("not registered in personal settings", result.stdout)
        self.assertEqual(self.pi_calls(), [])

    def test_scoped_npm_packages_are_supported(self):
        source = "npm:@example/tools"
        (self.repo / "agents/pi/packages.txt").write_text(source + "\n")
        self.successful_install("pi")
        self.assertEqual(self.pi_calls()[0]["args"], ["install", source])
        self.assertTrue((self.home / ".pi/agent/npm/node_modules/@example/tools/package.json").is_file())


if __name__ == "__main__":
    unittest.main()
