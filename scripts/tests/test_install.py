"""Install regression tests using an isolated repository and HOME."""

import json
import os
from pathlib import Path
import shutil
import subprocess
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
            self.env = dict(os.environ, HOME=str(self.home), SHELL="/bin/zsh")
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
        for relative in (".pi", ".claude", ".gemini", ".config/opencode"):
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
        self.assertFalse((self.home / ".pi").exists())

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
                self.assertFalse((self.home / ".pi").exists())

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
        self.assertFalse((self.home / ".pi").exists())
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
        for relative in (".pi", ".claude", ".gemini", ".config/opencode"):
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
        self.assertFalse((self.home / ".pi").exists())
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


if __name__ == "__main__":
    unittest.main()
