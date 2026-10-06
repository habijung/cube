"""실제 홈 파일, 프로세스, 클립보드를 사용하지 않는 세션 추적 회귀 테스트."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cmux_session.py"
SPEC = importlib.util.spec_from_file_location("cmux_session", SCRIPT)
cmux = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cmux)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.projects = self.root / "projects"
        self.runtime = self.root / "runtime"
        self.conversations = self.root / "conversations"
        self.save = self.root / "save"
        for path in (self.projects, self.runtime, self.conversations, self.save):
            path.mkdir()
        constants = {
            "CLAUDE_PROJECTS": str(self.projects), "CLAUDE_RUNTIME": str(self.runtime),
            "ANTIGRAVITY_CONVERSATIONS": str(self.conversations),
            "OPENCODE_DB": str(self.root / "opencode.db"),
            "SAVE_DIR": str(self.save), "SAVE_GLOB": str(self.save / "cmux-sessions-*.md"),
        }
        self.patch = mock.patch.multiple(cmux, **constants)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.kill = mock.patch.object(cmux.os, "kill")
        self.kill_mock = self.kill.start()
        self.addCleanup(self.kill.stop)
        self.clipboard = mock.patch.object(cmux, "copy_to_clipboard", return_value=True)
        self.copy_mock = self.clipboard.start()
        self.addCleanup(self.clipboard.stop)

    def candidate(self, sid=None, checkpoint=None, cwd="/work", kind="claude", title="test"):
        terminal = {}
        if sid is not None:
            terminal["agent"] = {"kind": kind, "sessionId": sid, "workingDirectory": cwd}
        else:
            terminal["resumeBinding"] = {"kind": kind, "checkpointId": checkpoint, "cwd": cwd}
        data = {"windows": [{"tabManager": {"workspaces": [{"customTitle": title,
                "panels": [{"terminal": terminal, "directory": cwd, "title": title,
                            "stableSurfaceId": title}]}]}}]}
        return cmux.collect_panels(data)[0]

    def record(self, sid="live", cwd="/work", kind="interactive", **kwargs):
        return dict(pid=123, sessionId=sid, cwd=cwd, kind=kind, **kwargs)

    def load(self, *records):
        for index, record in enumerate(records):
            (self.runtime / f"{index}.json").write_text(json.dumps(record))
        return cmux.load_claude_runtime()

    def resolve(self, candidates, *records):
        return cmux.resolve_panels(candidates, self.load(*records))

    def data(self, sid):
        project = self.projects / "project"
        project.mkdir(exist_ok=True)
        (project / f"{sid}.jsonl").write_text("{}\n")

    def saved_panel(self, sid="old", state="recorded", kind="claude", cwd="/work"):
        return dict(workspace="saved", kind=kind, sessionId=sid, cwd=cwd,
                    panelTitle="saved", launchArgs=[], resolution=state)

    def compare(self, panels, snapshot):
        return cmux.compare_saved_vs_current({"panels": panels}, snapshot)

    def save_fixture(self, panel):
        path = self.save / "fixture.md"
        path.write_text("```json\n" + json.dumps({"savedAt": "now", "panels": [panel]}) + "\n```\n")
        return cmux.read_save_file(str(path))

    def restore(self, panels, snapshot, arg=None):
        with mock.patch.object(cmux, "load_saved", return_value=("save", {"panels": panels})), \
                mock.patch.object(cmux, "require_current_snapshot", return_value=snapshot), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            cmux.cmd_restore(arg)
        return output.getvalue()

    def test_agent_priority_and_mismatch(self):
        candidate = self.candidate(sid="agent")
        candidate["checkpointId"] = "old"
        snapshot = self.resolve([candidate], self.record("live"))
        panel = snapshot["panels"][0]
        self.assertEqual((panel["sessionId"], panel["source"], panel["resolution"]),
                         ("agent", "agent", "recorded"))
        self.assertTrue(any("불일치" in w for w in panel["warnings"]))

    def test_binding_runtime_matches_without_data(self):
        snapshot = self.resolve([self.candidate(checkpoint="live")], self.record())
        panel = snapshot["panels"][0]
        self.assertEqual((panel["source"], panel["resolution"]), ("binding", "recorded"))
        self.assertEqual(cmux.cached_probe(snapshot["probe_cache"], panel), "absent")

    def test_binding_exists_preserved_even_with_different_runtime(self):
        self.data("old")
        panel = self.resolve([self.candidate(checkpoint="old")], self.record())["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))
        self.assertTrue(any("live" in w for w in panel["warnings"]))

    def test_binding_unknown_preserved(self):
        with mock.patch.object(cmux, "probe_session_data", return_value="unknown"):
            panel = self.resolve([self.candidate(checkpoint="old")], self.record())["panels"][0]
        self.assertEqual((panel["sessionId"], panel["source"]), ("old", "binding"))

    def test_absent_replaced(self):
        panel = self.resolve([self.candidate(checkpoint="old")], self.record())["panels"][0]
        self.assertEqual((panel["sessionId"], panel["source"], panel["resolution"]),
                         ("live", "runtime", "inferred"))

    def test_one_panel_two_candidates(self):
        snapshot = self.resolve([self.candidate()], self.record("a"), self.record("b"))
        self.assertEqual(snapshot["panels"], [])
        self.assertEqual(len(snapshot["unresolved"]), 1)

    def test_two_panels_one_candidate_order_independent(self):
        candidates = [self.candidate(checkpoint="a"), self.candidate(checkpoint="b")]
        runtime = self.load(self.record())
        for order in (candidates, list(reversed(candidates))):
            panels = cmux.resolve_panels(order, runtime)["panels"]
            self.assertEqual({p["sessionId"] for p in panels}, {"a", "b"})
            self.assertTrue(all(p["resolution"] == "unknown" for p in panels))

    def test_preserved_panel_blocks_other_owner(self):
        self.data("old")
        snapshot = self.resolve([self.candidate(checkpoint="old"), self.candidate()], self.record())
        self.assertEqual(len(snapshot["unresolved"]), 1)
        self.assertEqual([p["sessionId"] for p in snapshot["panels"]], ["old"])

    def test_reserved_runtime_not_reused(self):
        snapshot = self.resolve([self.candidate(sid="live"), self.candidate()], self.record())
        self.assertEqual(len(snapshot["panels"]), 1)
        self.assertEqual(len(snapshot["unresolved"]), 1)

    def test_absent_checkpoint_not_reserved(self):
        candidates = [self.candidate(checkpoint="live", cwd="/elsewhere"), self.candidate()]
        panels = self.resolve(candidates, self.record())["panels"]
        inferred = [p for p in panels if p["resolution"] == "inferred"]
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0]["cwd"], "/work")

    def test_unknown_path_blocks_inference(self):
        snapshot = self.resolve([self.candidate(), self.candidate(cwd=None)], self.record())
        self.assertEqual(len(snapshot["unresolved"]), 2)
        self.assertTrue(snapshot["runtime"]["global_block"])

    def test_bg_is_not_interactive_candidate(self):
        snapshot = self.resolve([self.candidate()], self.record(kind="bg", jobId="job"))
        self.assertEqual(len(snapshot["unresolved"]), 1)

    def test_non_claude_binding_unknown(self):
        for kind in ("opencode", "antigravity", "other"):
            with self.subTest(kind=kind):
                panel = self.resolve([self.candidate(checkpoint="id", kind=kind)])["panels"][0]
                self.assertEqual((panel["source"], panel["resolution"]), ("binding", "unknown"))

    def test_kind_conflict_does_not_mix_binding(self):
        data = {"windows": [{"tabManager": {"workspaces": [{"panels": [{"terminal": {
            "agent": {"kind": "claude", "sessionId": "agent"},
            "resumeBinding": {"kind": "opencode", "checkpointId": "binding", "cwd": "/wrong"}
        }, "directory": "/right"}]}]}}]}
        panel = cmux.collect_panels(data)[0]
        self.assertIsNone(panel["checkpointId"])
        self.assertEqual(panel["cwd"], "/right")

    def test_permission_error_adopted_with_warning(self):
        self.kill_mock.side_effect = PermissionError
        runtime = self.load(self.record())
        self.assertEqual(len(runtime["records"]), 1)
        self.assertTrue(runtime["records"][0]["warnings"])

    def test_dead_pid_removed(self):
        self.kill_mock.side_effect = ProcessLookupError
        runtime = self.load(self.record())
        self.assertEqual(runtime["records"], [])
        self.assertFalse(runtime["blocked"])

    def test_other_pid_error_blocks_path(self):
        self.kill_mock.side_effect = OSError
        runtime = self.load(self.record())
        self.assertIn(cmux.normalized_path("/work"), runtime["blocked"])
        self.assertFalse(runtime["global_block"])

    def test_invalid_pid_types_block_without_kill(self):
        for index, pid in enumerate((0, -1, True, "123", None)):
            record = self.record()
            record["pid"] = pid
            (self.runtime / f"{index}.json").write_text(json.dumps(record))
        runtime = cmux.load_claude_runtime()
        self.assertFalse(runtime["records"])
        self.assertTrue(runtime["blocked"])
        self.kill_mock.assert_not_called()

    def test_directory_failure_global_block(self):
        runtime = cmux.load_claude_runtime(str(self.root / "missing"))
        self.assertTrue(runtime["global_block"])

    def test_corrupt_file_retains_valid_record_but_blocks_inference(self):
        (self.runtime / "corrupt.json").write_text("{")
        runtime = self.load(self.record())
        self.assertEqual(len(runtime["records"]), 1)
        self.assertTrue(runtime["global_block"])
        panel = cmux.resolve_panels([self.candidate(checkpoint="live")], runtime)["panels"][0]
        self.assertEqual(panel["resolution"], "recorded")

    def test_path_error_blocks_only_affected_path(self):
        runtime = self.load(self.record("bad", pidDomain="unused"), self.record("good", cwd="/other"))
        # 별도의 잘못된 레코드로 /work만 불완전하게 합니다.
        bad = self.record("invalid")
        bad["kind"] = "unrecognized"
        (self.runtime / "invalid.json").write_text(json.dumps(bad))
        runtime = cmux.load_claude_runtime()
        self.assertIn(cmux.normalized_path("/work"), runtime["blocked"])
        self.assertFalse(runtime["global_block"])
        panel = cmux.resolve_panels([self.candidate(cwd="/other")], runtime)["panels"][0]
        self.assertEqual(panel["sessionId"], "good")

    def test_duplicate_auxiliary_fields_merge(self):
        runtime = self.load(self.record(updatedAt=1), self.record(updatedAt=2))
        self.assertEqual(len(runtime["records"]), 1)
        self.assertFalse(runtime["blocked"])

    def test_duplicate_core_conflict_blocks_paths(self):
        runtime = self.load(self.record(), self.record(cwd="/other"))
        self.assertFalse(runtime["records"])
        self.assertEqual(runtime["blocked"], {cmux.normalized_path("/work"), cmux.normalized_path("/other")})

    def test_parked_conflict_blocks_only_bg(self):
        runtime = self.load(self.record(parkedJobId="one"), self.record(parkedJobId="two"))
        self.assertEqual(len(runtime["records"]), 1)
        self.assertIsNone(runtime["records"][0]["parkedJobId"])
        self.assertFalse(runtime["blocked"])

    def test_parked_full_id(self):
        snapshot = self.resolve([self.candidate()], self.record(parkedJobId="job"),
                                self.record("full-bg-id", kind="bg", jobId="job"))
        self.assertEqual(snapshot["panels"][0]["parked"], "full-bg-id")
        self.assertEqual(len(snapshot["panels"]), 1)

    def test_parked_ambiguous_or_wrong_path(self):
        for mode in ("duplicate", "wrong-path", "none"):
            for filename in self.runtime.iterdir():
                filename.unlink()
            records = [self.record(parkedJobId="job")]
            if mode == "duplicate":
                records += [self.record("bg1", kind="bg", jobId="job"),
                            self.record("bg2", kind="bg", jobId="job")]
            elif mode == "wrong-path":
                records.append(self.record("bg", kind="bg", jobId="job", cwd="/other"))
            panel = self.resolve([self.candidate()], *records)["panels"][0]
            self.assertNotIn("parked", panel)
            self.assertIn("bg 연결 보류", panel["warnings"])

    def test_parked_blocked_on_incomplete_runtime(self):
        (self.runtime / "broken.json").write_text("{")
        snapshot = self.resolve([self.candidate(sid="live")], self.record(parkedJobId="job"),
                                self.record("bg", kind="bg", jobId="job"))
        self.assertNotIn("parked", snapshot["panels"][0])

    def test_probe_claude_states_and_cache(self):
        self.assertEqual(cmux.probe_session_data("claude", "id", "/work"), "absent")
        self.data("id")
        self.assertEqual(cmux.probe_session_data("claude", "id", "/work"), "exists")
        with mock.patch.object(cmux.os, "scandir", side_effect=PermissionError):
            self.assertEqual(cmux.probe_session_data("claude", "missing", "/work"), "unknown")
        with mock.patch.object(cmux, "probe_session_data", return_value="exists") as probe:
            snapshot = self.resolve([self.candidate(sid="id")])
            with contextlib.redirect_stdout(io.StringIO()):
                cmux.print_panel_rows(snapshot["panels"], snapshot["probe_cache"])
            cmux.write_save_file(snapshot["panels"], snapshot["probe_cache"])
            probe.assert_called_once()

    def test_probe_sqlite_readonly_and_error(self):
        connection = sqlite3.connect(cmux.OPENCODE_DB)
        connection.execute("CREATE TABLE session (id TEXT)")
        connection.execute("INSERT INTO session VALUES ('id')")
        connection.commit()
        connection.close()
        self.assertEqual(cmux.probe_session_data("opencode", "id", "/work"), "exists")
        self.assertEqual(cmux.probe_session_data("opencode", "missing", "/work"), "absent")
        with mock.patch.object(cmux.sqlite3, "connect", side_effect=sqlite3.OperationalError):
            self.assertEqual(cmux.probe_session_data("opencode", "id", "/work"), "unknown")

    def test_probe_antigravity_and_unknown_agent(self):
        (self.conversations / "id.db").write_text("")
        self.assertEqual(cmux.probe_session_data("antigravity", "id", None), "exists")
        self.assertEqual(cmux.probe_session_data("other", "id", None), "unknown")
        panel = self.saved_panel(kind="other")
        self.assertEqual(cmux.panel_mark(panel, {}), " ")

    def test_mark_absent_over_unknown_and_inferred(self):
        panel = self.saved_panel(state="unknown")
        self.assertEqual(cmux.panel_mark(panel, {}), "!")
        self.data("old")
        self.assertEqual(cmux.panel_mark(panel, {}), "?")
        panel["resolution"] = "inferred"
        self.assertEqual(cmux.panel_mark(panel, {}), "~")

    def test_symlink_paths_match(self):
        actual = self.root / "actual"
        actual.mkdir()
        link = self.root / "link"
        link.symlink_to(actual, target_is_directory=True)
        panel = self.resolve([self.candidate(cwd=str(link))],
                             self.record(cwd=str(actual)))["panels"][0]
        self.assertEqual(panel["resolution"], "inferred")

    def test_comparison_three_states_and_kind_key(self):
        snapshot = self.resolve([self.candidate(sid="a"), self.candidate(checkpoint="b")])
        result = self.compare([self.saved_panel("a"), self.saved_panel("b"),
                               self.saved_panel("c", cwd="/other"),
                               self.saved_panel("a", kind="opencode", cwd="/other")], snapshot)
        self.assertEqual([i for i, _ in result["matched"]], [1])
        self.assertEqual([i for i, _ in result["uncertain"]], [2])
        self.assertEqual([i for i, _ in result["missing"]], [3, 4])

    def test_recorded_wins_and_saved_unknown_can_upgrade(self):
        snapshot = self.resolve([self.candidate(checkpoint="id"), self.candidate(sid="id")])
        result = self.compare([self.saved_panel("id", "unknown")], snapshot)
        self.assertEqual(len(result["matched"]), 1)

    def test_unresolved_observation_not_missing(self):
        snapshot = self.resolve([self.candidate()])
        result = self.compare([self.saved_panel()], snapshot)
        self.assertEqual(len(result["uncertain"]), 1)

    def test_runtime_incomplete_not_missing(self):
        (self.runtime / "broken.json").write_text("{")
        result = self.compare([self.saved_panel()], self.resolve([]))
        self.assertEqual(len(result["uncertain"]), 1)

    def test_current_probe_unknown_not_missing(self):
        # 같은 경로의 현재 패널 데이터를 조회하지 못하면 관측이 불완전합니다.
        with mock.patch.object(cmux, "probe_session_data", return_value="unknown"):
            snapshot = self.resolve([self.candidate(sid="other")])
            result = self.compare([self.saved_panel()], snapshot)
        self.assertEqual(len(result["uncertain"]), 1)

    def test_saved_probe_unknown_alone_is_missing(self):
        # 저장 항목 자신의 조회 결과만으로는 누락 판정을 보류하지 않습니다.
        with mock.patch.object(cmux, "probe_session_data", return_value="unknown"):
            result = self.compare([self.saved_panel()], self.resolve([]))
        self.assertEqual(len(result["missing"]), 1)

    def test_unknown_agent_missing_can_auto_copy(self):
        # 저장 위치를 모르는 에이전트도 사라지면 누락으로 판정하고 자동 복사합니다.
        panel = self.saved_panel("id", kind="other")
        panel["launchArgs"] = ["other", "--session", "id"]
        result = self.compare([panel], self.resolve([]))
        self.assertEqual(len(result["missing"]), 1)
        self.restore([panel], self.resolve([]))
        self.copy_mock.assert_called_once()

    def test_pid_warning_only_on_runtime_evidence(self):
        self.kill_mock.side_effect = PermissionError
        snapshot = self.resolve(
            [self.candidate(sid="live"), self.candidate(cwd="/other")],
            self.record(), self.record("guess", cwd="/other"),
        )
        panels = {p["sessionId"]: p for p in snapshot["panels"]}
        self.assertFalse(any("PID" in w for w in panels["live"]["warnings"]))
        self.assertEqual(panels["guess"]["resolution"], "inferred")
        self.assertTrue(any("PID" in w for w in panels["guess"]["warnings"]))

    def test_restore_auto_only_recorded_missing(self):
        snapshot = self.resolve([])
        self.restore([self.saved_panel()], snapshot)
        self.copy_mock.assert_called_once()
        for state in ("inferred", "unknown"):
            self.copy_mock.reset_mock()
            self.restore([self.saved_panel(state=state)], snapshot)
            self.copy_mock.assert_not_called()

    def test_restore_uncertain_explicit_number(self):
        snapshot = self.resolve([self.candidate(checkpoint="old")])
        self.restore([self.saved_panel()], snapshot)
        self.copy_mock.assert_not_called()
        output = self.restore([self.saved_panel()], snapshot, "1")
        self.copy_mock.assert_called_once()
        self.assertIn("이미 실행 중", output)

    def test_restore_stable_number_and_multiple_candidates(self):
        snapshot = self.resolve([self.candidate(sid="a")])
        saved = [self.saved_panel("a"), self.saved_panel("b"), self.saved_panel("c")]
        output = self.restore(saved, snapshot)
        self.copy_mock.assert_not_called()
        self.assertIn("[2]", output)
        self.assertIn("[3]", output)
        self.restore(saved, snapshot, "3")
        self.assertIn("--resume c", self.copy_mock.call_args.args[0])

    def test_old_save_format_and_invalid_new_fields(self):
        panel = self.saved_panel()
        panel.pop("resolution")
        self.assertEqual(self.save_fixture(panel)["panels"][0]["resolution"], "recorded")
        for invalid in ("infered", [], None, 1):
            with self.subTest(invalid=invalid):
                panel["resolution"] = invalid
                panel["warnings"] = "invalid"
                panel["parked"] = 123
                read = self.save_fixture(panel)["panels"][0]
                self.assertEqual(read["resolution"], "unknown")
                self.assertIsInstance(read["warnings"], list)
                self.assertNotIn("parked", read)
        panel.pop("resolution")
        panel["source"] = "runtime"
        self.assertEqual(self.save_fixture(panel)["panels"][0]["resolution"], "unknown")

    def test_save_roundtrip_and_bg_reference(self):
        snapshot = self.resolve([self.candidate()], self.record(parkedJobId="job"),
                                self.record("full-bg", kind="bg", jobId="job"))
        path = cmux.write_save_file(snapshot["panels"], snapshot["probe_cache"])
        saved = cmux.read_save_file(path)
        self.assertEqual(saved["panels"][0]["parked"], "full-bg")
        self.assertEqual(saved["panels"][0]["resolution"], "inferred")
        content = Path(path).read_text()
        self.assertIn("claude --resume live", content)
        self.assertIn("claude --resume full-bg", content)
        path2 = cmux.write_save_file(snapshot["panels"], snapshot["probe_cache"])
        self.assertNotEqual(path, path2)
        self.assertEqual(cmux.latest_save_file(), path2)

    def test_snapshot_read_failure_and_wrapper(self):
        path = self.root / "cmux.json"
        for content in ("{", "[]", '{"windows": [{}], "extra": 1}', '{"windows": null}'):
            path.write_text(content)
            if content == '{"windows": [{}], "extra": 1}':
                self.assertEqual(cmux.read_panels(str(path)), [])
            else:
                self.assertIsNone(cmux.read_panels(str(path)))
        with mock.patch.object(cmux, "read_snapshot", return_value=None), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                cmux.require_current_snapshot()
        self.copy_mock.assert_not_called()

    def test_status_preserves_new_session_notice(self):
        snapshot = self.resolve([self.candidate(sid="new")])
        with mock.patch.object(cmux, "load_saved", return_value=("save", {"savedAt": "now", "panels": []})), \
                mock.patch.object(cmux, "require_current_snapshot", return_value=snapshot), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            cmux.cmd_status()
        self.assertIn("저장 이후 새로 생긴 세션 1개", output.getvalue())

    def test_invalid_resolution_cannot_auto_copy(self):
        panel = self.saved_panel()
        panel["resolution"] = "infered"
        saved = self.save_fixture(panel)
        self.restore(saved["panels"], self.resolve([]))
        self.copy_mock.assert_not_called()
        self.assertTrue(saved["panels"][0]["warnings"])

    def test_missing_resolution_runtime_cannot_auto_copy(self):
        panel = self.saved_panel()
        panel.pop("resolution")
        panel["source"] = "runtime"
        self.restore(self.save_fixture(panel)["panels"], self.resolve([]))
        self.copy_mock.assert_not_called()

    def test_pid_overflow_is_incomplete(self):
        self.kill_mock.side_effect = OverflowError
        runtime = self.load(self.record())
        self.assertTrue(runtime["blocked"])
        self.assertEqual(runtime["records"], [])

    def test_invalid_nul_path_does_not_crash(self):
        self.assertIsNone(cmux.normalized_path("/work\x00"))
        runtime = self.load(self.record(cwd="/work\x00"))
        self.assertTrue(runtime["global_block"])

    def test_resolve_does_not_mutate_runtime_completeness(self):
        runtime = self.load(self.record())
        first = cmux.resolve_panels([self.candidate(cwd=None)], runtime)
        self.assertTrue(first["runtime"]["global_block"])
        self.assertFalse(runtime["global_block"])
        second = cmux.resolve_panels([self.candidate()], runtime)
        self.assertEqual(second["panels"][0]["resolution"], "inferred")

    def test_omitted_surface_id_roundtrip_has_no_false_warning(self):
        candidate = self.candidate(sid="live")
        candidate["surfaceId"] = None
        panel = self.resolve([candidate])["panels"][0]
        self.assertNotIn("surfaceId", panel)
        read = self.save_fixture(panel)["panels"][0]
        self.assertFalse(any("surfaceId" in w for w in read["warnings"]))

    def test_required_save_fields_still_rejected(self):
        panel = self.saved_panel()
        panel["sessionId"] = ""
        self.assertIsNone(self.save_fixture(panel))

    def test_mark_override_preserves_warning_in_markdown(self):
        self.data("old")
        panel = self.resolve([self.candidate(checkpoint="old")])["panels"][0]
        (self.projects / "project" / "old.jsonl").unlink()
        cache = {}
        self.assertEqual(cmux.panel_mark(panel, cache), "!")
        path = cmux.write_save_file([panel], cache)
        content = Path(path).read_text()
        self.assertIn("판정 상태: unknown", content)
        self.assertIn("checkpoint 실행 연결 미확인", content)

    def test_launch_args_and_quoting_preserved(self):
        panel = self.saved_panel("id", kind="antigravity", cwd="/a'b")
        panel["launchArgs"] = ["antigravity", "--resume", "id"]
        command = cmux.resume_command(panel)
        self.assertIn("antigravity --resume id", command)
        self.assertIn("'\"'\"'", command)


if __name__ == "__main__":
    unittest.main()
