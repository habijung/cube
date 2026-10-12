"""실제 홈 파일, 프로세스, 클립보드를 사용하지 않는 세션 추적 회귀 테스트."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
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
        self.assertEqual(cmux.panel_mark(panel, {}), "*")

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

    def test_save_roundtrip_without_bg_reference(self):
        snapshot = self.resolve([self.candidate()], self.record(parkedJobId="job"),
                                self.record("full-bg", kind="bg", jobId="job"))
        path = cmux.write_save_file(snapshot["panels"], snapshot["probe_cache"])
        saved = cmux.read_save_file(path)
        self.assertNotIn("parked", saved["panels"][0])
        self.assertEqual(saved["panels"][0]["resolution"], "inferred")
        content = Path(path).read_text()
        self.assertIn("claude --resume live", content)
        self.assertNotIn("claude --resume full-bg", content)
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

    def transcript(self, sid, target=None, cwd="/work", events=None):
        project = self.projects / "project"
        project.mkdir(exist_ok=True)
        if events is None:
            events = [dict(type="user", sessionId=sid, cwd=cwd,
                           timestamp="2026-09-28T00:00:00Z", message={"content": "fixture"})]
            if target:
                events.append(dict(type="continued-in", sessionId=sid,
                                   continuedInSessionId=target, timestamp="2026-09-28T01:00:00Z"))
        path = project / f"{sid}.jsonl"
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
        return path

    def continuation_fixture(self):
        self.transcript("old", "new")
        self.transcript("new")
        return self.record("old", parkedJobId="job"), self.record("new", kind="bg", jobId="job")

    def test_continuation_recorded_single_target(self):
        records = self.continuation_fixture()
        panel = self.resolve([self.candidate(sid="old")], *records)["panels"][0]
        self.assertEqual((panel["sessionId"], panel["source"], panel["resolution"]),
                         ("new", "agent", "recorded"))
        self.assertEqual(panel["originSessionId"], "old")
        self.assertEqual(panel["continuation"], ["old", "new"])
        self.assertNotIn("parked", panel)
        self.assertEqual(cmux.panel_mark(panel, {}), " ")

    def test_continuation_inferred_remains_inferred(self):
        records = self.continuation_fixture()
        snapshot = self.resolve([self.candidate()], *records)
        panel = snapshot["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("new", "inferred"))
        self.assertEqual(cmux.panel_mark(panel, {}), "*")
        for p in self.runtime.iterdir():
            p.unlink()
        self.restore([panel], self.resolve([]))
        self.copy_mock.assert_not_called()

    def test_continuation_unknown_not_promoted(self):
        self.continuation_fixture()
        panel = self.resolve([self.candidate(checkpoint="old")])["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("new", "unknown"))

    def test_bg_direct_agent_and_binding(self):
        self.transcript("new")
        for candidate in (self.candidate(sid="new"), self.candidate(checkpoint="new")):
            panel = self.resolve([candidate], self.record("new", kind="bg", jobId="job"))["panels"][0]
            self.assertEqual((panel["sessionId"], panel["resolution"]), ("new", "recorded"))
            self.assertEqual(cmux.panel_mark(panel, {}), " ")

    def test_parked_alone_does_not_select_bg(self):
        self.transcript("old")
        self.transcript("new")
        panel = self.resolve([self.candidate(sid="old")], self.record("old", parkedJobId="job"),
                             self.record("new", kind="bg", jobId="job"))["panels"][0]
        self.assertEqual(panel["sessionId"], "old")
        self.assertNotIn("continuation", panel)

    def test_direct_bg_reserves_interactive_ancestor(self):
        records = self.continuation_fixture()
        for candidates in ([self.candidate(sid="new"), self.candidate()],
                           [self.candidate(), self.candidate(sid="new")]):
            for p in self.runtime.iterdir():
                p.unlink()
            snapshot = self.resolve(candidates, *records)
            self.assertEqual([p["sessionId"] for p in snapshot["panels"]], ["new"])
            self.assertEqual(len(snapshot["unresolved"]), 1)

    def test_continuation_multiple_hops(self):
        self.transcript("old", "middle")
        self.transcript("middle", "new")
        self.transcript("new")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual(panel["sessionId"], "new")
        self.assertEqual(panel["continuation"], ["old", "middle", "new"])

    def test_continuation_cycle_and_depth_limit(self):
        self.transcript("old", "new")
        self.transcript("new", "old")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))
        self.transcript("new")
        with mock.patch.object(cmux, "CLAUDE_CONTINUATION_LIMIT", 1):
            panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual(panel["resolution"], "unknown")

    def test_continuation_missing_target(self):
        self.transcript("old", "missing")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))
        self.restore([panel], self.resolve([]))
        self.copy_mock.assert_not_called()

    def test_continuation_empty_target_and_wrong_path(self):
        self.transcript("old", "new")
        for events in ([], [dict(type="user", sessionId="new", cwd="/other")]):
            self.transcript("new", events=events)
            panel = self.resolve([self.candidate(sid="old")])["panels"][0]
            self.assertEqual(panel["resolution"], "unknown")

    def test_continuation_runtime_conflict(self):
        self.transcript("old", "new")
        self.transcript("new")
        panel = self.resolve([self.candidate(sid="old")], self.record("old", parkedJobId="job"),
                             self.record("different", kind="bg", jobId="job"))["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))

    def test_transcript_conflicting_links(self):
        path = self.transcript("old", "new")
        with path.open("a") as f:
            f.write(json.dumps(dict(type="continued-in", sessionId="old",
                                    continuedInSessionId="other", timestamp="2026-09-28T02:00:00Z")) + "\n")
        self.transcript("new")
        self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")

    def test_original_resumed_after_continuation(self):
        path = self.transcript("old", "new")
        with path.open("a") as f:
            f.write(json.dumps(dict(type="user", sessionId="old", cwd="/work",
                                    timestamp="2026-09-28T03:00:00Z")) + "\n")
        self.transcript("new")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual(panel["resolution"], "unknown")

    def test_original_newer_timestamp_before_marker(self):
        self.transcript("old", events=[
            dict(type="user", sessionId="old", cwd="/work", timestamp="2026-09-28T03:00:00Z"),
            dict(type="continued-in", sessionId="old", continuedInSessionId="new",
                 timestamp="2026-09-28T01:00:00Z"),
        ])
        self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")

    def test_transcript_duplicate_files(self):
        path = self.transcript("old")
        duplicate = self.projects / "other"
        duplicate.mkdir()
        (duplicate / path.name).write_bytes(path.read_bytes())
        self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")

    def test_transcript_corrupt_and_size_limit(self):
        path = self.transcript("old")
        with mock.patch.object(cmux, "CLAUDE_TRANSCRIPT_LIMIT", 10):
            self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")
        for invalid in ("{\n", "[]\n", "\xff\n"):
            path.write_text(invalid)
            self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")

    def test_transcript_permission_error_and_cache(self):
        self.transcript("old")
        cache = {}
        with mock.patch("builtins.open", wraps=open) as opened:
            first = cmux.load_claude_transcript("old", cache)
            self.assertIs(first, cmux.load_claude_transcript("old", cache))
            opened.assert_called_once()
        with mock.patch.object(cmux.os, "scandir", side_effect=PermissionError):
            self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")

    def test_continuation_malformed_metadata(self):
        for changes in ({"sessionId": "wrong"}, {"continuedInSessionId": []},
                        {"timestamp": 123}, {"timestamp": "invalid"},
                        {"timestamp": "2026-09-28T00:00:00"}):
            link = dict(type="continued-in", sessionId="old", continuedInSessionId="new",
                        timestamp="2026-09-28T01:00:00Z")
            link.update(changes)
            self.transcript("old", events=[link])
            with self.subTest(changes=changes):
                self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")
        for sid in (None, [], {}, True, 1, "../old", "old/new", "old\\new", "old\x00"):
            self.assertEqual(cmux.load_claude_transcript(sid, {})["state"], "unknown")

    def test_saved_old_id_matches_current_continuation(self):
        records = self.continuation_fixture()
        snapshot = self.resolve([self.candidate(sid="new")], *records)
        saved = self.saved_panel()
        result = self.compare([saved], snapshot)
        self.assertEqual([i for i, _ in result["matched"]], [1])
        self.assertEqual(result["matched"][0][1]["sessionId"], "new")
        self.assertFalse(result["added"])
        self.assertEqual(saved["sessionId"], "old")

    def test_common_ancestor_not_automatic_equivalence(self):
        self.transcript("old", "new")
        self.transcript("new")
        self.transcript("independent")
        snapshot = self.resolve([self.candidate(sid="independent")])
        saved = self.saved_panel("new")
        saved.update(originSessionId="old", continuation=["old", "new"])
        result = self.compare([saved], snapshot)
        self.assertEqual(len(result["missing"]), 1)
        self.assertEqual(len(result["added"]), 1)

    def test_restore_old_id_uses_final_id_and_stable_number(self):
        self.transcript("old", "new")
        self.transcript("new")
        snapshot = self.resolve([self.candidate(sid="matched", cwd="/other")])
        saved = [self.saved_panel("matched", cwd="/other"), self.saved_panel()]
        output = self.restore(saved, snapshot, "2")
        self.assertIn("[2]", output)
        self.assertIn("--resume new", self.copy_mock.call_args.args[0])
        self.assertNotIn("--resume old", self.copy_mock.call_args.args[0])

    def test_live_bg_without_panel_uncertain_and_attach(self):
        records = self.continuation_fixture()
        snapshot = self.resolve([], *records)
        result = self.compare([self.saved_panel()], snapshot)
        self.assertEqual(len(result["uncertain"]), 1)
        self.restore([self.saved_panel()], snapshot)
        self.copy_mock.assert_not_called()
        self.restore([self.saved_panel()], snapshot, "1")
        self.assertIn("claude attach job", self.copy_mock.call_args.args[0])

    def test_offline_final_id_can_auto_copy_when_recorded(self):
        self.transcript("old", "new")
        self.transcript("new")
        self.restore([self.saved_panel()], self.resolve([]))
        self.assertIn("--resume new", self.copy_mock.call_args.args[0])

    def test_live_interactive_without_panel_not_auto_copy(self):
        self.restore([self.saved_panel("live")], self.resolve([], self.record()))
        self.copy_mock.assert_not_called()

    def test_resume_command_bg_requires_unique_complete_runtime(self):
        panel = self.saved_panel("new")
        runtime = self.load(self.record("new", kind="bg", jobId="job's"))
        self.assertIn("claude attach 'job'\"'\"'s'", cmux.resume_command(panel, runtime))
        self.assertIn("--resume new", cmux.resume_command(panel))
        runtime["global_block"] = True
        self.assertIn("--resume new", cmux.resume_command(panel, runtime))
        runtime["global_block"] = False
        runtime["records"].append(dict(runtime["records"][0]))
        self.assertIn("--resume new", cmux.resume_command(panel, runtime))

    def test_continuation_saved_roundtrip_single_command_and_row(self):
        panel = self.resolve([self.candidate(sid="old")], *self.continuation_fixture())["panels"][0]
        path = cmux.write_save_file([panel])
        read = cmux.read_save_file(path)["panels"][0]
        self.assertEqual(read["continuation"], ["old", "new"])
        content = Path(path).read_text()
        self.assertEqual(content.count("claude --resume"), 1)
        self.assertIn("claude --resume new", content)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cmux.print_panel_rows([panel])
        self.assertIn("new", output.getvalue())
        self.assertNotIn("old", output.getvalue())
        self.assertNotIn("(bg:", output.getvalue())

    def test_invalid_saved_continuation_never_promoted(self):
        for chain in ("old", [], ["old"], ["old", "wrong"], ["old", "old"], [[], "new"]):
            panel = self.saved_panel("new")
            panel.update(originSessionId="old", continuation=chain)
            with self.subTest(chain=chain):
                read = self.save_fixture(panel)["panels"][0]
                self.assertEqual(read["resolution"], "unknown")
                self.assertNotIn("continuation", read)
                self.restore([read], self.resolve([]))
                self.copy_mock.assert_not_called()

    def test_saved_parked_not_trusted_as_resume_target(self):
        panel = self.saved_panel()
        panel["parked"] = "new"
        saved = self.save_fixture(panel)["panels"][0]
        self.assertEqual(saved["parked"], "new")
        self.restore([saved], self.resolve([]), "1")
        self.assertIn("--resume old", self.copy_mock.call_args.args[0])

    def test_marker_not_based_on_binding_or_mismatch(self):
        self.transcript("old")
        panel = self.saved_panel()
        panel.update(source="binding", warnings=["checkpoint 불일치"])
        self.assertEqual(cmux.panel_mark(panel, {}), " ")
        panel["resolution"] = "inferred"
        self.assertEqual(cmux.panel_mark(panel, {}), "*")

    def test_panel_rows_align_at_digit_boundaries(self):
        for total in (9, 12, 101):
            panels = [dict(self.saved_panel(str(i)), workspace="workspace")
                      for i in range(total)]
            with self.subTest(total=total), mock.patch.object(cmux, "panel_mark", return_value=" "), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                cmux.print_panel_rows(panels)
            rows = output.getvalue().splitlines()
            self.assertEqual(len({row.index("workspace") for row in rows}), 1)
            self.assertIn(f"[{1:>{len(str(total))}}]", rows[0])
            self.assertIn(f"[{total}]", rows[-1])

    def test_restore_number_width_uses_saved_total_not_remaining_count(self):
        saved = [dict(self.saved_panel(f"id-{i}"), workspace="workspace") for i in range(1, 101)]
        snapshot = self.resolve([self.candidate(sid=f"id-{i}") for i in range(1, 101)
                                 if i not in (9, 10)])
        output = self.restore(saved, snapshot)
        rows = [line for line in output.splitlines() if "workspace" in line]
        self.assertEqual(len(rows), 2)
        self.assertIn("[  9]", rows[0])
        self.assertIn("[ 10]", rows[1])
        self.assertEqual(rows[0].index("workspace"), rows[1].index("workspace"))
        self.copy_mock.assert_not_called()
        output = self.restore(saved, snapshot, "9")
        self.assertIn("[  9] workspace", output)
        self.assertIn("--resume id-9", self.copy_mock.call_args.args[0])

    def test_status_groups_share_saved_number_width(self):
        saved = {"savedAt": "fixture", "panels": [
            dict(self.saved_panel(f"id-{i}"), workspace="workspace") for i in range(1, 13)]}
        uncertain = dict(saved["panels"][8], resolution="unknown", warnings=["fixture warning"])
        missing = saved["panels"][9]
        added = dict(self.saved_panel("added"), workspace="workspace")
        result = {"matched": [], "uncertain": [(9, uncertain)],
                  "missing": [(10, missing)], "added": [added]}
        snapshot = self.resolve([])
        with mock.patch.object(cmux, "load_comparison", return_value=("fixture", saved, snapshot, result)), \
                mock.patch.object(cmux, "panel_mark", return_value=" "), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            cmux.cmd_status()
        rows = [line for line in output.getvalue().splitlines() if "workspace" in line]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row.index("workspace") for row in rows}), 1)
        self.assertIn("[ 9]", rows[0])
        self.assertIn("[10]", rows[1])
        self.assertIn("[ 1]", rows[2])

    def test_partial_tail_preserves_recorded_and_same_key_match(self):
        path = self.transcript("old")
        with path.open("ab") as f:
            f.write(b'{"type":"assistant","sessionId":"old')
        metadata = cmux.load_claude_transcript("old", {})
        self.assertEqual(metadata["state"], "exists")
        self.assertTrue(metadata["partial_tail"])
        self.assertFalse(metadata["seen_continuation"])
        snapshot = self.resolve([self.candidate(sid="old")])
        panel = snapshot["panels"][0]
        self.assertEqual(panel["resolution"], "recorded")
        self.assertEqual(cmux.panel_mark(panel, {}), " ")
        self.assertNotIn("_continuation_blocked", panel)
        self.assertTrue(panel["_resume_unverified"])
        self.assertEqual(len(self.compare([self.saved_panel()], snapshot)["matched"]), 1)
        self.restore([self.saved_panel()], self.resolve([]))
        self.copy_mock.assert_not_called()

    def test_complete_json_without_newline_is_validated(self):
        path = self.transcript("old", "new")
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
        self.transcript("new")
        metadata = cmux.load_claude_transcript("old", {})
        self.assertEqual(metadata["state"], "exists")
        self.assertTrue(metadata["seen_continuation"])
        self.assertFalse(metadata["partial_tail"])
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("new", "recorded"))
        self.assertNotIn("_resume_unverified", panel)

    def test_complete_message_without_newline_allows_offline_auto_copy(self):
        path = self.transcript("old")
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
        self.restore([self.saved_panel()], self.resolve([]))
        self.assertIn("--resume old", self.copy_mock.call_args.args[0])

    def test_newline_corruption_unknown_but_preserves_binding(self):
        path = self.transcript("old")
        with path.open("a") as f:
            f.write('{"type":"assistant"\n')
        self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")
        panel = self.resolve([self.candidate(checkpoint="old")], self.record("old"))["panels"][0]
        self.assertEqual(panel["resolution"], "recorded")
        self.assertNotIn("_continuation_blocked", panel)
        self.assertTrue(panel["_resume_unverified"])

    def test_size_limit_preserves_linkage_not_auto_copy(self):
        self.transcript("old")
        with mock.patch.object(cmux, "CLAUDE_TRANSCRIPT_LIMIT", 10):
            snapshot = self.resolve([self.candidate(sid="old")])
            panel = snapshot["panels"][0]
            self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "recorded"))
            self.assertNotIn("_continuation_blocked", panel)
            self.assertTrue(panel["_resume_unverified"])
            self.assertTrue(any("이어짐 확인 불가" in w for w in panel["warnings"]))
            self.assertEqual(len(self.compare([self.saved_panel()], snapshot)["matched"]), 1)
            self.restore([self.saved_panel()], self.resolve([]))
            self.copy_mock.assert_not_called()

    def test_duplicate_preserves_recorded_match_not_auto_copy(self):
        path = self.transcript("old")
        duplicate = self.projects / "other"
        duplicate.mkdir()
        (duplicate / path.name).write_bytes(path.read_bytes())
        snapshot = self.resolve([self.candidate(sid="old")])
        panel = snapshot["panels"][0]
        self.assertEqual(panel["resolution"], "recorded")
        self.assertNotIn("_continuation_blocked", panel)
        self.assertEqual(len(self.compare([self.saved_panel()], snapshot)["matched"]), 1)
        self.restore([self.saved_panel()], self.resolve([]))
        self.copy_mock.assert_not_called()

    def test_permission_failure_preserves_recorded_match(self):
        self.transcript("old")
        with mock.patch("builtins.open", side_effect=PermissionError):
            snapshot = self.resolve([self.candidate(sid="old")])
            panel = snapshot["panels"][0]
            self.assertEqual(panel["resolution"], "recorded")
            self.assertTrue(panel["_resume_unverified"])
            self.assertNotIn("_continuation_blocked", panel)
            self.assertEqual(len(self.compare([self.saved_panel()], snapshot)["matched"]), 1)
            self.restore([self.saved_panel()], self.resolve([]))
            self.copy_mock.assert_not_called()

    def recursion_parser(self):
        """버전별 JSON 중첩 허용 깊이에 무관하게 파서 실패를 재현합니다."""
        parser = json.loads

        def parse(value, *args, **kwargs):
            if isinstance(value, bytes) and value.startswith(b'{"nested":'):
                raise RecursionError("fixture: JSON nesting limit")
            return parser(value, *args, **kwargs)

        return mock.patch.object(cmux.json, "loads", side_effect=parse)

    def test_recursion_failure_preserves_recorded_match_not_auto_copy(self):
        path = self.transcript("old")
        with path.open("a") as f:
            f.write('{"nested":[]}')
        with self.recursion_parser():
            metadata = cmux.load_claude_transcript("old", {})
            self.assertEqual(metadata["state"], "unknown")
            self.assertFalse(metadata["seen_continuation"])
            self.assertFalse(metadata["partial_tail"])
            snapshot = self.resolve([self.candidate(sid="old")])
            panel = snapshot["panels"][0]
            self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "recorded"))
            self.assertTrue(panel["_resume_unverified"])
            self.assertNotIn("_continuation_blocked", panel)
            self.assertEqual(len(self.compare([self.saved_panel()], snapshot)["matched"]), 1)
            self.restore([self.saved_panel()], self.resolve([]))
            self.copy_mock.assert_not_called()
            output = self.restore([self.saved_panel()], self.resolve([]), "1")
            self.assertIn("이어짐 확인이 불완전", output)
            self.assertIn("--resume old", self.copy_mock.call_args.args[0])

    def test_recursion_failure_after_continuation_still_blocks(self):
        path = self.transcript("old", "new")
        with path.open("a") as f:
            f.write('{"nested":[]}\n')
        self.transcript("new")
        with self.recursion_parser():
            metadata = cmux.load_claude_transcript("old", {})
            self.assertEqual(metadata["state"], "unknown")
            self.assertTrue(metadata["seen_continuation"])
            self.assertFalse(metadata["partial_tail"])
            panel = self.resolve([self.candidate(sid="old")])["panels"][0]
            self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))
            self.assertTrue(panel["_continuation_blocked"])
            self.restore([self.saved_panel()], self.resolve([]))
            self.copy_mock.assert_not_called()

    def test_recursion_failure_in_successor_still_blocks(self):
        self.transcript("old", "new")
        path = self.transcript("new")
        with path.open("a") as f:
            f.write('{"nested":[]}\n')
        with self.recursion_parser():
            panel = self.resolve([self.candidate(sid="old")])["panels"][0]
            self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))
            self.assertTrue(panel["_continuation_blocked"])
            result = self.compare([self.saved_panel()], self.resolve([]))
            self.assertEqual(len(result["uncertain"]), 1)
            self.assertFalse(result["missing"])
            self.restore([self.saved_panel()], self.resolve([]))
            self.copy_mock.assert_not_called()

    def test_native_nested_json_isolated_on_parser_limit(self):
        depth = sys.getrecursionlimit() + 100
        payload = b'{"nested":' + b"[" * depth + b"0" + b"]" * depth + b"}\n"
        try:
            json.loads(payload)
            expected = "exists"
        except RecursionError:
            expected = "unknown"
        path = self.transcript("old")
        with path.open("ab") as f:
            f.write(payload)
        self.assertLess(path.stat().st_size, cmux.CLAUDE_TRANSCRIPT_LIMIT)
        metadata = cmux.load_claude_transcript("old", {})
        self.assertEqual(metadata["state"], expected)
        self.assertFalse(metadata["partial_tail"])
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual(panel["resolution"], "recorded")
        if expected == "unknown":
            self.assertTrue(panel["_resume_unverified"])
            self.restore([self.saved_panel()], self.resolve([]))
            self.copy_mock.assert_not_called()

    def test_seen_continuation_flag_precedes_link_validation(self):
        self.transcript("old", events=[dict(type="continued-in", sessionId="wrong")])
        metadata = cmux.load_claude_transcript("old", {})
        self.assertTrue(metadata["seen_continuation"])
        self.assertEqual(metadata["state"], "unknown")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual(panel["resolution"], "unknown")
        self.assertTrue(panel["_continuation_blocked"])

    def test_partial_tail_after_continuation_still_blocks(self):
        path = self.transcript("old", "new")
        with path.open("a") as f:
            f.write('{"type":"user"')
        self.transcript("new")
        metadata = cmux.load_claude_transcript("old", {})
        self.assertEqual(metadata["state"], "unknown")
        self.assertTrue(metadata["seen_continuation"])
        self.assertTrue(metadata["partial_tail"])
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual(panel["resolution"], "unknown")
        self.assertTrue(panel["_continuation_blocked"])

    def test_partial_tail_in_successor_still_blocks(self):
        self.transcript("old", "new")
        path = self.transcript("new")
        with path.open("a") as f:
            f.write('{"type":"assistant"')
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))
        self.assertTrue(panel["_continuation_blocked"])
        self.restore([self.saved_panel()], self.resolve([]))
        self.copy_mock.assert_not_called()

    def test_limit_after_seen_continuation_still_blocks(self):
        path = self.transcript("old", "new")
        limit = path.stat().st_size
        with path.open("a") as f:
            f.write("{}\n")
        self.transcript("new")
        with mock.patch.object(cmux, "CLAUDE_TRANSCRIPT_LIMIT", limit):
            metadata = cmux.load_claude_transcript("old", {})
            self.assertTrue(metadata["seen_continuation"])
            self.assertEqual(metadata["state"], "unknown")
            panel = self.resolve([self.candidate(sid="old")])["panels"][0]
            self.assertEqual(panel["resolution"], "unknown")
            self.assertTrue(panel["_continuation_blocked"])

    def test_inferred_unknown_not_promoted_by_query_failure(self):
        self.transcript("old").write_text("{\n")
        for state in ("inferred", "unknown"):
            panel = self.saved_panel(state=state)
            result = cmux.resolve_continuation(panel, self.load(), {})
            self.assertEqual(result["resolution"], state)
            self.assertTrue(result["_resume_unverified"])
            self.assertNotIn("_continuation_blocked", result)

    def test_failed_query_keeps_path_candidate_id(self):
        self.transcript("live").write_text("{\n")
        panel = self.resolve([self.candidate()], self.record())["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("live", "inferred"))
        self.assertEqual(cmux.panel_mark(panel, {}), "*")

    def test_failed_query_explicit_copy_warns_but_does_not_execute(self):
        self.transcript("old").write_text("{\n")
        output = self.restore([self.saved_panel()], self.resolve([]), "1")
        self.assertIn("이어짐 확인이 불완전", output)
        self.assertIn("--resume old", self.copy_mock.call_args.args[0])

    def test_resume_uncertainty_not_serialized_and_rechecked(self):
        self.transcript("old").write_text("{\n")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        path = cmux.write_save_file([panel])
        saved = cmux.read_save_file(path)["panels"][0]
        self.assertEqual(saved["resolution"], "recorded")
        self.assertNotIn("_resume_unverified", saved)
        self.restore([saved], self.resolve([]))
        self.copy_mock.assert_not_called()

    def test_transcript_disappearing_during_read_is_unknown(self):
        self.transcript("old")
        with mock.patch("builtins.open", side_effect=FileNotFoundError):
            self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")

    def test_comparison_does_not_mutate_saved_or_current_panels(self):
        records = self.continuation_fixture()
        snapshot = self.resolve([self.candidate(sid="new")], *records)
        saved = {"panels": [self.saved_panel()]}
        before_saved = json.dumps(saved, sort_keys=True)
        before_current = json.dumps(snapshot["panels"], sort_keys=True)
        self.compare(saved["panels"], snapshot)
        self.assertEqual(json.dumps(saved, sort_keys=True), before_saved)
        self.assertEqual(json.dumps(snapshot["panels"], sort_keys=True), before_current)

    def test_saved_failure_reason_shown_in_restore(self):
        self.transcript("old", "missing")
        output = self.restore([self.saved_panel()], self.resolve([]))
        self.assertIn("근거/경고", output)
        self.assertIn("이어진 대화 조회/작업 경로 확인 불가", output)
        self.copy_mock.assert_not_called()

    def test_saved_continuation_failure_is_uncertain_not_missing(self):
        self.transcript("old", "missing")
        snapshot = self.resolve([self.candidate(sid="other")])
        result = self.compare([self.saved_panel()], snapshot)
        self.assertEqual(len(result["uncertain"]), 1)
        self.assertFalse(result["missing"])
        self.restore([self.saved_panel()], snapshot)
        self.copy_mock.assert_not_called()

    def test_parked_conflict_blocks_continuation(self):
        self.transcript("old", "new")
        self.transcript("new")
        panel = self.resolve([self.candidate(sid="old")],
                             self.record("old", parkedJobId="one"),
                             self.record("old", parkedJobId="two"))["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("old", "unknown"))

    def test_transcript_permission_to_one_project_not_absent(self):
        original = cmux.os.stat
        self.transcript("old")
        denied = self.projects / "denied"
        denied.mkdir()

        def stat(path, *args, **kwargs):
            if str(path) == str(denied / "old.jsonl"):
                raise PermissionError
            return original(path, *args, **kwargs)

        with mock.patch.object(cmux.os, "stat", side_effect=stat):
            self.assertEqual(cmux.load_claude_transcript("old", {})["state"], "unknown")

    def test_private_continuation_state_not_serialized(self):
        self.transcript("old", "missing")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertTrue(panel["_continuation_blocked"])
        path = cmux.write_save_file([panel])
        saved = cmux.read_save_file(path)
        self.assertEqual(saved["panels"][0]["resolution"], "unknown")
        self.assertNotIn("_continuation_blocked", saved["panels"][0])

    def test_historical_cwd_changes_do_not_invalidate_current_record(self):
        events = [dict(type="user", sessionId="old", cwd="/past",
                       timestamp="2026-09-27T00:00:00Z"),
                  dict(type="user", sessionId="old", cwd="/work",
                       timestamp="2026-09-28T00:00:00Z")]
        self.transcript("old", events=events)
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual(panel["resolution"], "recorded")
        events.append(dict(type="continued-in", sessionId="old", continuedInSessionId="new",
                           timestamp="2026-09-28T01:00:00Z"))
        self.transcript("old", events=events)
        self.transcript("new")
        panel = self.resolve([self.candidate(sid="old")])["panels"][0]
        self.assertEqual((panel["sessionId"], panel["resolution"]), ("new", "recorded"))

    def test_star_legend_and_no_tilde(self):
        self.transcript("live")
        snapshot = self.resolve([self.candidate()], self.record())
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cmux.print_diagnostics(snapshot)
        self.assertIn("* 추정 연결", output.getvalue())
        self.assertNotIn("~", output.getvalue())


if __name__ == "__main__":
    unittest.main()
