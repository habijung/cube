#!/usr/bin/env python3
"""cmux 패널의 에이전트 세션을 저장하고, 복원되지 않은 세션의 재개 명령어를 안내합니다.

cmux가 자체 세션 파일(session-com.cmuxterm.app.json)에 기록해 둔 패널 정보를 읽어
에이전트 세션의 재개 명령어를 파일로 남깁니다. cmux 복원이 실패했을 때 저장 목록과
현재 열린 패널을 대조해 누락된 세션만 골라냅니다.

cmux가 agent 정보를 지운 패널은 resumeBinding과 Claude runtime 기록
(~/.claude/sessions)으로 보완합니다. recorded는 기록 일치이며 실행 중임을 보장하지
않습니다. 경로로 추정한 연결은 inferred로 구분하고 자동 복사하지 않습니다.

저장 파일은 `cmux-sessions-<YYMMDD-HHMM>.md` 형식이며, `status`와 `restore`는
가장 최근 파일을 자동으로 선택합니다. 복구가 끝난 파일은 삭제해도 무방합니다.

표준 라이브러리만 사용하며 cmux와 각 에이전트의 세션 저장소를 읽기 전용으로
조회합니다.

Usage:
    cmux_session.py                   status 실행 (기본값)
    cmux_session.py list              현재 패널의 세션 기록 출력 (저장하지 않음)
    cmux_session.py save              식별 가능한 세션 기록을 새 저장 파일로 저장
    cmux_session.py status            최근 저장과 현재 기록을 대조 (일치·확인 필요·누락)
    cmux_session.py restore           누락·확인 필요 목록과 재개 명령 출력
    cmux_session.py restore <번호>    저장 당시 번호의 복구 후보 명령을 복사 (필요 시 경고)

Restore:
    자동 복사는 전체 복구 후보가 1개이고, 관측이 완전한 누락이며,
    저장 당시 recorded였을 때만 합니다. 번호 지정은 확인 필요 항목도 경고 후 복사합니다.
    재개 명령을 대신 실행하지 않습니다. 검토한 뒤 각각 다른 패널에서 실행하세요.

Env:
    CUBE_CMUX_SAVE_DIR    저장 디렉토리 (기본: ~/Desktop)
"""

import datetime
import glob
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys

CMUX_DIR = os.path.expanduser("~/Library/Application Support/cmux")
SESSION_FILE = os.path.join(CMUX_DIR, "session-com.cmuxterm.app.json")
SAVE_DIR = os.path.expanduser(os.environ.get("CUBE_CMUX_SAVE_DIR", "~/Desktop"))
SAVE_PREFIX = "cmux-sessions-"
SAVE_GLOB = os.path.join(SAVE_DIR, f"{SAVE_PREFIX}*.md")
# 파일명 타임스탬프: YYMMDD-HHMM (예: cmux-sessions-260908-1712.md)
# 같은 분에 두 번 저장하면 -2, -3 접미사가 붙습니다.
SAVE_PATTERN = re.compile(rf"{re.escape(SAVE_PREFIX)}(\d{{6}}-\d{{4}})(?:-(\d+))?\.md$")
CLAUDE_PROJECTS = os.path.expanduser("~/.claude/projects")
# Claude가 실행 중인 세션마다 남기는 내부 기록(<pid>.json)입니다. 공식 계약이 아닙니다.
CLAUDE_RUNTIME = os.path.expanduser("~/.claude/sessions")
OPENCODE_DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
ANTIGRAVITY_CONVERSATIONS = os.path.expanduser("~/.gemini/antigravity-cli/conversations")


# --- 입력 조회 ---------------------------------------------------------------


def text(value):
    """비어 있지 않은 문자열만 돌려줍니다. 그 밖의 값은 None입니다."""
    if isinstance(value, str) and value.strip() and "\x00" not in value:
        return value
    return None


def normalized_path(path):
    """경로 비교용 정규화입니다. 심볼릭 링크를 풀고, 대소문자는 바꾸지 않습니다."""
    if not text(path):
        return None
    try:
        return os.path.realpath(os.path.abspath(path))
    except (OSError, ValueError):
        return None


def probe_session_data(kind, session_id, cwd):
    """세션 데이터(대화 기록)가 디스크에 남아 있는지 확인합니다.

    exists: 데이터 있음 / absent: 정상 조회 결과 없음 / unknown: 조회 실패 또는 미지원
    조회 오류를 absent로 숨기지 않습니다. absent는 checkpoint 교체 근거가 되기 때문입니다.
    """
    # 저장 위치를 모르는 에이전트는 판정을 보류합니다.
    # 데이터가 있는데 '!'를 붙이면 잘못된 경고가 되기 때문입니다.
    if kind not in ("claude", "opencode", "antigravity"):
        return "unknown"
    # ID를 파일 이름으로 쓰므로 경로 구분자가 섞인 값은 조회하지 않습니다.
    if not text(session_id) or "/" in session_id or session_id in (".", ".."):
        return "unknown"
    try:
        if kind == "opencode":
            # opencode는 세션을 SQLite DB에 보관합니다.
            # stat는 권한 오류를 FileNotFoundError와 구분합니다.
            os.stat(OPENCODE_DB)
            connection = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
            try:
                found = connection.execute(
                    "SELECT 1 FROM session WHERE id = ? LIMIT 1", (session_id,)
                ).fetchone()
            finally:
                connection.close()
            return "exists" if found else "absent"
        if kind == "antigravity":
            # 대화는 conversations/<id>.db에 저장됩니다 (구버전은 .pb).
            with os.scandir(ANTIGRAVITY_CONVERSATIONS) as entries:
                found = any(e.name.startswith(session_id + ".") for e in entries)
            return "exists" if found else "absent"

        # glob는 디렉토리 권한 오류를 빈 결과로 숨기므로 사용하지 않습니다.
        filename = session_id + ".jsonl"
        if text(cwd):
            # cmux의 cwd -> claude 프로젝트 디렉토리 슬러그 ('/'와 '.'이 '-'로 바뀝니다)
            slug = cwd.replace("/", "-").replace(".", "-")
            try:
                os.stat(os.path.join(CLAUDE_PROJECTS, slug, filename))
                return "exists"
            except FileNotFoundError:
                pass
        # 슬러그 규칙이 어긋날 수 있으므로 전체 프로젝트에서 한 번 더 찾습니다
        with os.scandir(CLAUDE_PROJECTS) as entries:
            projects = [e.path for e in entries if e.is_dir()]
        incomplete = False
        for project in projects:
            try:
                os.stat(os.path.join(project, filename))
                return "exists"
            except FileNotFoundError:
                pass
            except OSError:
                incomplete = True
        return "unknown" if incomplete else "absent"
    except FileNotFoundError:
        return "absent"
    except (OSError, sqlite3.Error):
        return "unknown"


def cached_probe(cache, panel):
    """한 명령 안에서 같은 세션의 데이터 조회를 한 번만 수행합니다."""
    key = (panel["kind"], panel["sessionId"], normalized_path(panel.get("cwd")))
    if key not in cache:
        cache[key] = probe_session_data(*key)
    return cache[key]


def collect_panels(data):
    """agent 또는 resumeBinding이 있는 터미널 패널을 후보로 수집합니다.

    세션 ID는 아직 정하지 않고 agentId와 checkpointId를 그대로 보존합니다.
    잘못된 cmux 구조는 호출부(read_snapshot)에서 읽기 실패로 처리합니다.
    """
    panels = []
    for window in data.get("windows", []):
        for ws in window.get("tabManager", {}).get("workspaces", []):
            title = (
                text(ws.get("customTitle"))
                or os.path.basename(text(ws.get("currentDirectory")) or "")
                or "(무제)"
            )
            for panel in ws.get("panels", []):
                terminal = panel.get("terminal") or {}
                agent = terminal.get("agent") or {}
                # cmux가 agent를 지운 패널도 재개 정보(resumeBinding)는 남아 있을 수 있습니다.
                binding = terminal.get("resumeBinding") or {}
                if not agent and not binding:
                    continue

                kind = text(agent.get("kind")) or text(binding.get("kind"))
                warnings = []
                # 종류가 다른 binding의 ID와 경로를 agent 정보와 섞지 않습니다.
                if (
                    text(agent.get("kind"))
                    and text(binding.get("kind"))
                    and agent["kind"] != binding["kind"]
                ):
                    binding = {}
                    warnings.append("agent와 binding 종류 불일치: agent 우선")

                cwd_sources = (
                    agent.get("workingDirectory"),
                    binding.get("cwd"),
                    terminal.get("workingDirectory"),
                    panel.get("directory"),
                )
                cwd = next((value for value in cwd_sources if text(value)), None)

                # cmux가 기록해 둔 실행 인자입니다.
                # 재개 방법을 모르는 에이전트는 이걸로 명령어를 복원합니다.
                launch = agent.get("launchCommand") or binding.get("launchCommand") or {}
                launch_args = launch.get("arguments") or []
                if not isinstance(launch_args, list) or kind in ("claude", "opencode"):
                    launch_args = []

                panels.append(
                    {
                        "workspace": title,
                        "kind": kind,
                        "cwd": cwd,
                        "panelTitle": text(panel.get("title")) or "",
                        "launchArgs": launch_args,
                        "surfaceId": text(panel.get("stableSurfaceId")),
                        "agentId": text(agent.get("sessionId")),
                        "checkpointId": text(binding.get("checkpointId")),
                        "warnings": warnings,
                    }
                )
    return panels


def load_claude_runtime(path=None):
    """Claude runtime 기록과, 조회가 불완전해 추정을 보류할 범위를 함께 돌려줍니다.

    blocked는 추정을 보류할 정규화 경로 집합이고, global_block은 경로를 알 수 없는
    오류가 있어 모든 경로의 추정을 보류해야 한다는 뜻입니다.
    """
    path = CLAUDE_RUNTIME if path is None else path
    result = {"records": [], "blocked": set(), "global_block": False, "diagnostics": []}

    def block(cwd, reason):
        if cwd:
            result["blocked"].add(cwd)
        else:
            result["global_block"] = True
        result["diagnostics"].append(reason)

    try:
        with os.scandir(path) as entries:
            files = sorted(e.path for e in entries if e.name.endswith(".json"))
    except OSError:
        block(None, "Claude runtime 디렉토리 조회 불가: 추정 보류")
        return result

    # 레코드 단위로 오류를 격리합니다. 손상된 파일이 있어도 정상 레코드는 유지합니다.
    records = []
    for filename in files:
        cwd = None
        try:
            with open(filename) as f:
                record = json.load(f)
            if not isinstance(record, dict):
                raise ValueError
            cwd = normalized_path(record.get("cwd"))
            pid = record.get("pid")
            # bool은 int의 하위 타입이므로 PID로 허용하지 않도록 먼저 걸러냅니다.
            valid_pid = isinstance(pid, int) and not isinstance(pid, bool) and pid > 0
            if (
                not cwd
                or not text(record.get("sessionId"))
                or record.get("kind") not in ("interactive", "bg")
                or not valid_pid
            ):
                raise ValueError
        except (OSError, ValueError):
            block(cwd, f"runtime 레코드 읽기/형식 오류: {os.path.basename(filename)}")
            continue

        record = dict(record, cwd=cwd, warnings=[])
        # signal 0은 프로세스 존재만 확인합니다. PID 재사용은 구분하지 못합니다.
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            # 다른 사용자의 프로세스이거나 sandbox 안에서 실행한 경우입니다.
            record["warnings"].append("PID 확인 제한: 프로세스 동일성은 확인하지 못함")
        except (OSError, OverflowError):
            block(cwd, f"runtime PID 확인 불가: {os.path.basename(filename)}")
            continue
        for key in ("jobId", "parkedJobId"):
            record[key] = text(record.get(key))
        records.append(record)

    # 같은 세션의 레코드는 핵심 필드(종류, 경로, bg의 jobId)로만 비교합니다.
    # pid, updatedAt, status 같은 부수 필드가 달라도 같은 세션으로 봅니다.
    groups = {}
    for record in records:
        groups.setdefault(record["sessionId"], []).append(record)
    for session_id, group in groups.items():
        cores = {
            (r["kind"], r["cwd"], r["jobId"] if r["kind"] == "bg" else None)
            for r in group
        }
        if len(cores) != 1:
            for record in group:
                block(record["cwd"], f"runtime 핵심 필드 충돌: {session_id}")
            continue
        record = dict(group[0])
        record["warnings"] = sorted({w for r in group for w in r["warnings"]})
        # parkedJobId 충돌은 세션 추정이 아니라 bg 연결만 보류합니다.
        if len({r["parkedJobId"] for r in group}) != 1:
            record["parkedJobId"] = None
            record["warnings"].append("parkedJobId 충돌: bg 연결 보류")
        result["records"].append(record)
    return result


def runtime_blocked(runtime, cwd):
    """해당 경로의 runtime 관측이 불완전해 추정을 보류해야 하는지 확인합니다."""
    return runtime["global_block"] or cwd in runtime["blocked"]


def resolve_panels(candidates, runtime, probe_cache=None):
    """패널마다 세션 ID와 그 근거(source)·판정 상태(resolution)를 정합니다.

    1차: 모든 패널을 agent → checkpoint 순으로 판정하고 확정된 ID를 예약합니다.
    2차: 미확정 Claude 패널과 예약되지 않은 runtime 세션이 같은 경로에서 양쪽 모두
         정확히 하나일 때만 연결합니다(inferred). 패널 순서는 결과에 영향을 주지 않습니다.
    """
    cache = {} if probe_cache is None else probe_cache
    # 호출자가 같은 runtime 관찰값으로 다시 해결해도 이전 보류 상태가 누적되지 않습니다.
    runtime = dict(runtime, blocked=set(runtime["blocked"]))
    snapshot = {
        "panels": [],
        "unresolved": [],
        "diagnostics": list(runtime["diagnostics"]),
        "probe_cache": cache,
        "runtime": runtime,
    }
    interactive = {
        r["sessionId"]: r for r in runtime["records"] if r["kind"] == "interactive"
    }

    # --- 1차: 패널별 판정과 예약 ---
    claimed = set()
    pending = []
    for candidate in candidates:
        panel = {
            key: value
            for key, value in candidate.items()
            if key not in ("agentId", "checkpointId")
        }
        panel["warnings"] = list(panel["warnings"])
        if panel.get("surfaceId") is None:
            panel.pop("surfaceId", None)
        panel.update(source="unknown", resolution="unknown")
        panel["sessionId"] = candidate["agentId"] or candidate["checkpointId"]
        # replace: 2차에서 runtime 세션으로 교체해도 되는지 여부
        replace = not candidate["agentId"]
        cwd = normalized_path(panel["cwd"])

        if not panel["kind"]:
            panel["warnings"].append("agent 종류 확인 불가")
            snapshot["unresolved"].append(panel)
            continue

        if candidate["agentId"]:
            panel.update(source="agent", resolution="recorded")
            checkpoint_id = candidate["checkpointId"]
            if checkpoint_id and checkpoint_id != candidate["agentId"]:
                panel["warnings"].append("agent ID와 cmux checkpoint 불일치")
        elif candidate["checkpointId"]:
            # 대화를 아직 쓰지 않은 새 세션도 있으므로 runtime 일치를 먼저 확인합니다.
            record = interactive.get(panel["sessionId"]) if panel["kind"] == "claude" else None
            if record and cwd and record["cwd"] == cwd:
                panel.update(source="binding", resolution="recorded")
                replace = False
            else:
                # 데이터가 있거나(exists) 조회하지 못한(unknown) checkpoint는 보존합니다.
                # 정상 조회로 데이터가 없음(absent)을 확인한 Claude checkpoint만 교체합니다.
                # 비-Claude는 runtime 확인 수단이 없어 항상 보존(binding/unknown)합니다.
                state = cached_probe(cache, panel)
                if state != "absent" or panel["kind"] != "claude":
                    panel["source"] = "binding"
                    replace = False
                panel["warnings"].append("checkpoint 실행 연결 미확인")
                if state == "unknown":
                    panel["warnings"].append("checkpoint 데이터 조회 불가")

        # recorded ID와 보존된 checkpoint는 다른 패널의 runtime 후보에서 제외합니다.
        if panel["resolution"] == "recorded" or (panel["sessionId"] and not replace):
            claimed.add((panel["kind"], panel["sessionId"]))
        pending.append((panel, replace))

    # --- 2차: 경로별 일괄 매칭 (Claude 전용) ---
    # 보존된 checkpoint 패널도 같은 runtime의 소유 후보이므로 그룹에 포함합니다.
    # 교체되지는 않지만 다른 패널이 그 runtime을 가져가는 것을 막습니다.
    owners = {}
    unknown_path = False
    for panel, replace in pending:
        if panel["kind"] == "claude" and panel["resolution"] != "recorded":
            cwd = normalized_path(panel["cwd"])
            if cwd:
                owners.setdefault(cwd, []).append((panel, replace))
            else:
                unknown_path = True
    # 종류 불명 패널도 Claude 소유 가능성을 배제할 수 없습니다.
    unknown_path = unknown_path or bool(snapshot["unresolved"])
    if unknown_path:
        runtime["global_block"] = True
        snapshot["diagnostics"].append("경로/종류 불명 미확정 패널: Claude 추정 전체 보류")

    for cwd, group in owners.items():
        available = [
            r
            for r in interactive.values()
            if r["cwd"] == cwd and ("claude", r["sessionId"]) not in claimed
        ]
        unique = len(group) == 1 and len(available) == 1
        if not runtime_blocked(runtime, cwd) and unique and group[0][1]:
            panel = group[0][0]
            old_id = panel["sessionId"]
            panel.update(
                sessionId=available[0]["sessionId"], source="runtime", resolution="inferred"
            )
            panel["warnings"].append("경로 기반 추정: 외부 터미널과 구분 불가")
            if old_id and old_id != panel["sessionId"]:
                panel["warnings"].append("cmux checkpoint와 불일치")
        else:
            for panel, _ in group:
                panel["warnings"].append("runtime 매칭 보류")
                if available:
                    candidates_text = ", ".join(r["sessionId"] for r in available)
                    panel["warnings"].append("runtime 후보: " + candidates_text)

    # --- 마무리: ID 없는 패널 분리, runtime 경고와 bg 연결 ---
    for panel, _ in pending:
        if not panel["sessionId"]:
            panel["warnings"].append("세션 ID 확인 불가: 저장에서 제외")
            snapshot["unresolved"].append(panel)
            continue

        record = interactive.get(panel["sessionId"]) if panel["kind"] == "claude" else None
        if record:
            # runtime 레코드의 경고(PID 확인 제한 등)는 그 레코드를 근거로 ID를 정한
            # 패널에만 붙입니다. agent 기록으로 정해진 패널에 붙이면 잡음만 늘어납니다.
            uses_runtime = panel["source"] in ("binding", "runtime")
            if uses_runtime:
                panel["warnings"].extend(record["warnings"])
            job = record.get("parkedJobId")
            if job:
                bg = [
                    r
                    for r in runtime["records"]
                    if r["kind"] == "bg" and r["jobId"] == job and r["cwd"] == record["cwd"]
                ]
                if (
                    len(bg) == 1
                    and not runtime_blocked(runtime, record["cwd"])
                    and normalized_path(panel["cwd"]) == record["cwd"]
                ):
                    panel["parked"] = bg[0]["sessionId"]
                    if uses_runtime:
                        panel["warnings"].extend(bg[0]["warnings"])
                else:
                    panel["warnings"].append("bg 연결 보류")

        cached_probe(cache, panel)
        panel["warnings"] = list(dict.fromkeys(panel["warnings"]))
        snapshot["panels"].append(panel)
    return snapshot


def read_snapshot(path=SESSION_FILE):
    """cmux 세션 파일과 runtime을 한 번씩 읽어 해결된 snapshot을 만듭니다.

    cmux 파일을 읽지 못하면 None입니다. 빈 목록으로 대신하면 저장된 세션이
    모두 누락으로 분류되므로 호출부에서 중단합니다.
    """
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("windows"), list):
            return None
        candidates = collect_panels(data)
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return resolve_panels(candidates, load_claude_runtime())


def read_panels(path=SESSION_FILE):
    """기존 호출 계약을 유지합니다. 명령은 진단을 보존하는 snapshot을 사용합니다."""
    snapshot = read_snapshot(path)
    return None if snapshot is None else snapshot["panels"]


# --- 재개 명령과 저장 파일 ---------------------------------------------------


def resume_command(panel):
    """패널을 재개하는 셸 명령어를 만듭니다."""
    session_id = panel["sessionId"]

    if not panel["cwd"]:
        return f"# 작업 경로를 알 수 없습니다 — {panel['kind']} 세션 {session_id}"

    # 경로에 작은따옴표가 들어가도 명령어가 깨지지 않도록 이스케이프합니다
    cwd = shlex.quote(panel["cwd"])
    quoted_session_id = shlex.quote(str(session_id))
    if panel["kind"] == "claude":
        return f"cd {cwd} && claude --resume {quoted_session_id}"
    if panel["kind"] == "opencode":
        return f"cd {cwd} && opencode --session {quoted_session_id}"

    # 그 밖의 에이전트는 cmux가 기록한 실행 인자를 그대로 재사용합니다.
    # antigravity처럼 인자에 세션 식별자가 포함된 경우 이대로 재개됩니다.
    launch_args = panel.get("launchArgs") or []
    if any(session_id in str(arg) for arg in launch_args):
        return f"cd {cwd} && {shlex.join(str(arg) for arg in launch_args)}"

    return f"cd {cwd}  # {panel['kind']} 세션 {session_id} (재개 방법 미상)"


def latest_save_file():
    """가장 최근 저장 파일의 경로를 돌려줍니다. 없으면 None입니다."""
    candidates = []
    for path in glob.glob(SAVE_GLOB):
        matched = SAVE_PATTERN.search(path)
        if matched:
            # (타임스탬프, 접미사) 순으로 비교합니다.
            # 이름순 정렬은 '-2.md'가 '.md'보다 앞서므로 쓸 수 없습니다.
            serial = int(matched.group(2)) if matched.group(2) else 1
            candidates.append(((matched.group(1), serial), path))

    if not candidates:
        return None
    return max(candidates)[1]


def resolution(panel):
    """패널의 판정 상태를 돌려줍니다. 잘못된 값은 recorded로 승격하지 않습니다."""
    value = panel.get("resolution")
    if value in ("recorded", "inferred", "unknown"):
        return value
    if "resolution" in panel or panel.get("source") in ("runtime", "unknown"):
        return "unknown"
    # 새 필드가 없는 구형 저장 항목은 예전 동작대로 cmux 기록으로 취급합니다.
    return "recorded"


def write_save_file(panels, probe_cache=None, diagnostics=None):
    """사람이 읽는 목록과 restore가 파싱할 JSON을 한 파일에 담습니다."""
    cache = {} if probe_cache is None else probe_cache
    now = datetime.datetime.now()
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # 같은 분에 만든 파일의 최대 번호 다음을 사용해 삭제된 번호를 재사용하지 않습니다.
    os.makedirs(SAVE_DIR, exist_ok=True)
    file_stamp = now.strftime("%y%m%d-%H%M")
    base = os.path.join(SAVE_DIR, f"{SAVE_PREFIX}{file_stamp}")
    serials = []
    for existing in glob.glob(f"{base}*.md"):
        matched = SAVE_PATTERN.search(existing)
        if matched and matched.group(1) == file_stamp:
            serials.append(int(matched.group(2)) if matched.group(2) else 1)
    serial = max(serials, default=0) + 1
    path = f"{base}.md" if serial == 1 else f"{base}-{serial}.md"

    lines = [
        "# cmux 세션 복구 명령어",
        "",
        f"- 저장 시각: {stamp}",
        f"- 세션 수: {len(panels)}",
        "",
        "복원이 실패하거나 확인이 필요하면 아래 명령을 검토한 뒤 새 패널에 붙여넣으세요.",
        "복구가 끝나면 이 파일은 삭제해도 됩니다.",
        "",
    ]
    for message in diagnostics or []:
        lines.append(f"- 진단: {message}")
    lines.append("")

    data_labels = {"exists": "O", "absent": "X (세션 데이터 없음)", "unknown": "확인 불가"}
    for index, panel in enumerate(panels, start=1):
        lines += [
            f"## [{index}] {panel['workspace']} — {panel['kind']}",
            "",
            f"- 패널 제목: {panel['panelTitle']}",
            f"- 작업 경로: {panel['cwd']}",
            f"- 세션 데이터: {data_labels[cached_probe(cache, panel)]}",
            f"- ID 근거: {panel.get('source', 'agent')}",
            f"- 판정 상태: {resolution(panel)}",
        ]
        lines.extend(f"- 경고: {warning}" for warning in panel.get("warnings", []))
        lines += [
            "",
            "```sh",
            resume_command(panel),
            "```",
            "",
        ]
        # bg 세션은 패널 복구 대상이 아니므로 참고용으로만 덧붙입니다.
        if panel.get("parked"):
            bg = dict(panel, sessionId=panel["parked"])
            lines += [
                "bg 참고용 재개 명령 (패널 복구 명령과 별개):",
                "",
                "```sh",
                resume_command(bg),
                "```",
                "",
            ]

    # restore가 읽는 기계용 블록입니다. 번호는 이 목록의 순서를 그대로 따릅니다.
    lines += [
        "---",
        "",
        "## 데이터",
        "",
        "`/cube-cmux restore`가 읽는 블록입니다. 직접 편집하지 마세요.",
        "",
        "```json",
        json.dumps({"savedAt": stamp, "panels": panels}, ensure_ascii=False, indent=2),
        "```",
        "",
        f"**Updated At:** {now.strftime('%Y. %-m. %-d.')}",
        "",
    ]

    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def read_save_file(path):
    """저장 파일의 JSON 블록을 되읽습니다. 새 필드는 있을 때만 검사합니다."""
    try:
        with open(path) as f:
            content = f.read()
    except (OSError, UnicodeError):
        return None

    # 마지막 ```json 블록을 꺼냅니다.
    # 패널 제목은 에이전트가 자동 생성하므로 백틱이 섞일 수 있습니다.
    # 여는/닫는 fence가 각각 독립된 줄일 때만 인식해 본문 문자열과 구분합니다.
    blocks = re.findall(
        r"^```json[ \t]*\r?\n(.*?)^```[ \t]*$", content, re.MULTILINE | re.DOTALL
    )
    if not blocks:
        return None
    try:
        saved = json.loads(blocks[-1])
    except ValueError:
        return None
    if not isinstance(saved, dict):
        return None
    if not isinstance(saved.get("savedAt"), str) or not isinstance(saved.get("panels"), list):
        return None
    for panel in saved["panels"]:
        if not isinstance(panel, dict):
            return None
        if not all(isinstance(panel.get(key), str) and panel[key]
                   for key in ("workspace", "kind", "sessionId")):
            return None
        if "cwd" not in panel or not isinstance(panel["cwd"], (str, type(None))):
            return None
        if not isinstance(panel.get("launchArgs", []), list):
            return None

        # 새 필드는 잘못되어도 파일 전체를 거부하지 않고 그 필드만 무효로 처리합니다.
        warnings = panel.get("warnings", [])
        if not isinstance(warnings, list) or not all(isinstance(w, str) for w in warnings):
            warnings = ["저장된 warnings 형식 오류"]
        panel["warnings"] = list(warnings)
        if "resolution" in panel and panel["resolution"] not in ("recorded", "inferred", "unknown"):
            panel["warnings"].append("저장된 resolution 형식 오류: 확인 필요")
        panel["resolution"] = resolution(panel)
        if "source" in panel and panel["source"] not in ("agent", "binding", "runtime", "unknown"):
            panel.pop("source")
            panel["warnings"].append("저장된 source 형식 오류")
            panel["resolution"] = "unknown"
        for key in ("surfaceId", "parked"):
            if key in panel and not text(panel[key]):
                panel.pop(key)
                panel["warnings"].append(f"저장된 {key} 형식 오류")
        if not isinstance(panel.get("panelTitle"), str):
            panel["panelTitle"] = ""
    return saved


def copy_to_clipboard(value):
    try:
        subprocess.run(["pbcopy"], input=value.encode(), check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


# --- snapshot 대조 -----------------------------------------------------------


def panel_key(panel):
    """세션 동일성 키입니다. 종류가 다른 에이전트의 ID 충돌을 막습니다."""
    return panel["kind"], panel["sessionId"]


def observation_incomplete(panel, snapshot):
    """저장된 세션이 현재 기록에 없을 때, 현재 쪽 관측이 불완전한지 확인합니다.

    같은 종류·경로에 ID 없는 패널, 미확정 패널, 데이터 조회 실패가 있거나
    runtime 추정이 보류되었다면 "누락"으로 단정하지 않습니다.
    저장 항목 자신의 데이터 조회 결과는 보지 않습니다. 저장 위치를 모르는
    에이전트는 조회 결과가 항상 unknown이라 영영 누락으로 판정되지 않기 때문입니다.
    """
    kind, cwd = panel["kind"], normalized_path(panel.get("cwd"))
    runtime = snapshot["runtime"]
    if kind == "claude" and (not cwd or runtime_blocked(runtime, cwd)):
        return True
    for current in snapshot["panels"] + snapshot["unresolved"]:
        current_kind = current.get("kind")
        current_cwd = normalized_path(current.get("cwd"))
        # 종류나 경로를 모르는 현재 패널은 관련 가능성을 배제할 수 없습니다.
        if current_kind and current_kind != kind:
            continue
        if cwd and current_cwd and cwd != current_cwd:
            continue
        if not current.get("sessionId") or resolution(current) != "recorded":
            return True
        if cached_probe(snapshot["probe_cache"], current) == "unknown":
            return True
    return False


def compare_saved_vs_current(saved, snapshot):
    """저장 목록을 현재 snapshot과 대조해 기록 일치·확인 필요·누락·신규로 나눕니다."""
    # 같은 키가 여러 패널에 있으면 recorded를 우선합니다.
    states = {}
    for current in snapshot["panels"]:
        key = panel_key(current)
        value = "matched" if resolution(current) == "recorded" else "uncertain"
        if states.get(key) != "matched":
            states[key] = value
    # 번호는 저장 시점의 순서를 유지합니다. 복구가 진행돼도 번호가 밀리지 않습니다.
    result = {"matched": [], "uncertain": [], "missing": [], "added": []}
    for index, panel in enumerate(saved["panels"], start=1):
        state = states.get(panel_key(panel))
        if state is None:
            state = "uncertain" if observation_incomplete(panel, snapshot) else "missing"
        result[state].append((index, panel))
    saved_keys = {panel_key(p) for p in saved["panels"]}
    result["added"] = [p for p in snapshot["panels"] if panel_key(p) not in saved_keys]
    return result


# --- 출력과 명령 -------------------------------------------------------------


def require_current_snapshot():
    snapshot = read_snapshot()
    if snapshot is None:
        print(f"cmux 세션 파일을 읽을 수 없습니다 (없거나 손상됨): {SESSION_FILE}")
        sys.exit(1)
    return snapshot


def require_current_panels():
    return require_current_snapshot()["panels"]


def panel_mark(panel, cache):
    """한 글자 요약 표시입니다. 우선순위는 ! → ? → ~ 입니다."""
    # 세션 데이터가 없음을 확인했습니다 (조회 실패는 '!'가 아니라 진단으로 표시)
    if cached_probe(cache, panel) == "absent":
        return "!"
    # 세션 연결을 확정하지 못했습니다
    if resolution(panel) == "unknown":
        return "?"
    # 경로 추정, binding만으로 수집됨, 또는 cmux checkpoint와 불일치
    if (
        resolution(panel) == "inferred"
        or panel.get("source") == "binding"
        or any("불일치" in warning for warning in panel.get("warnings", []))
    ):
        return "~"
    return " "


def print_panel_rows(panels, probe_cache=None):
    """패널 목록을 한 줄씩 출력합니다. save와 list가 같은 형식을 씁니다."""
    cache = {} if probe_cache is None else probe_cache
    for index, panel in enumerate(panels, start=1):
        print_panel_row(index, panel, cache)


def print_panel_row(index, panel, cache):
    mark = panel_mark(panel, cache)
    bg = f"  (bg: {panel['parked'][:8]})" if panel.get("parked") else ""
    print(
        f"  [{index}]{mark} {panel['workspace']:16} {panel['kind']:9} "
        f"{panel['sessionId'][:8]}{bg}"
    )


def snapshot_messages(snapshot):
    """runtime 진단과 저장에서 제외된 패널을 사용자용 문장으로 만듭니다."""
    messages = list(snapshot["diagnostics"])
    for panel in snapshot["unresolved"]:
        kind = panel.get("kind") or "?"
        cwd = panel.get("cwd") or "경로 불명"
        reasons = "; ".join(panel["warnings"])
        messages.append(f"저장 제외: {panel['workspace']} / {kind} / {cwd} — {reasons}")
    return messages


def print_diagnostics(snapshot):
    """표시 설명, 패널별 경고, 진단을 출력합니다. 해당하는 것이 있을 때만 나옵니다."""
    cache = snapshot["probe_cache"]
    marks = {panel_mark(p, cache) for p in snapshot["panels"]}
    descriptions = {
        "!": "세션 데이터가 없음을 확인했습니다.",
        "?": "세션 연결을 확정하지 못했습니다. 확인이 필요합니다.",
        "~": "cmux 기록이 불완전하거나 추정된 연결입니다. 재시작 전 save를 권장합니다.",
    }
    for mark in ("!", "?", "~"):
        if mark in marks:
            print(f"\n  {mark} {descriptions[mark]}")

    for panel in snapshot["panels"]:
        warnings = list(panel["warnings"])
        if cached_probe(cache, panel) == "unknown":
            warnings.append("세션 데이터 조회 불가")
        if warnings:
            print(f"  {panel['workspace']} ({panel['sessionId'][:8]}): " + "; ".join(warnings))

    for message in snapshot_messages(snapshot):
        print(f"  진단: {message}")


def cmd_list():
    snapshot = require_current_snapshot()
    print(f"현재 세션 기록 {len(snapshot['panels'])}개\n")
    print_panel_rows(snapshot["panels"], snapshot["probe_cache"])
    print_diagnostics(snapshot)
    print("\n저장하려면: /cube-cmux save")


def cmd_save():
    snapshot = require_current_snapshot()
    panels = snapshot["panels"]
    if not panels:
        print("저장 가능한 세션 ID가 없습니다.")
        print_diagnostics(snapshot)
        return

    previous = latest_save_file()
    path = write_save_file(panels, snapshot["probe_cache"], snapshot_messages(snapshot))

    print(f"저장 완료: {path}")
    print(f"세션 {len(panels)}개\n")
    print_panel_rows(panels, snapshot["probe_cache"])
    print_diagnostics(snapshot)

    # 세션 수가 줄었다면 복원 실패 상태에서 저장했을 가능성을 알립니다
    if previous:
        old = read_save_file(previous)
        if old and len(old["panels"]) > len(panels):
            print(
                f"\n⚠️  직전 저장({os.path.basename(previous)})은 {len(old['panels'])}개였습니다."
            )
            print("   복원 실패 상태에서 저장했을 수 있습니다.")
            print("   누락 세션은 이전 파일에 남아 있으니 지우지 마세요.")


def load_saved():
    """최근 저장 파일을 읽어 (경로, 데이터)를 돌려줍니다."""
    path = latest_save_file()
    if path is None:
        print(f"저장 파일이 없습니다: {SAVE_GLOB}")
        print("먼저 `/cube-cmux save`를 실행해 주세요.")
        sys.exit(1)

    saved = read_save_file(path)
    if saved is None:
        print(f"저장 파일을 읽을 수 없습니다: {path}")
        print("JSON 블록이 손상되었을 수 있습니다. `/cube-cmux save`로 새로 저장해 주세요.")
        sys.exit(1)

    return path, saved


def load_comparison():
    """저장 목록과 현재 snapshot을 읽어 대조 결과까지 함께 돌려줍니다."""
    path, saved = load_saved()
    snapshot = require_current_snapshot()
    return path, saved, snapshot, compare_saved_vs_current(saved, snapshot)


def cmd_status():
    path, saved, snapshot, result = load_comparison()
    total = len(saved["panels"])

    print(f"저장 파일: {os.path.basename(path)} ({saved['savedAt']})")
    print(
        f"저장 {total}개 / 기록 일치 {len(result['matched'])}개 / "
        f"확인 필요 {len(result['uncertain'])}개 / 누락 {len(result['missing'])}개\n"
    )

    for key, label in (("uncertain", "확인 필요"), ("missing", "누락")):
        if result[key]:
            print(label + ":")
            for index, panel in result[key]:
                print_panel_row(index, panel, snapshot["probe_cache"])
    if result["uncertain"] or result["missing"]:
        print("\n복구 명령을 확인하려면: /cube-cmux restore")
    else:
        print("저장된 세션이 모두 cmux 기록과 일치합니다. 실행 중임을 보장하지는 않습니다.")

    if result["added"]:
        print(f"\n저장 이후 새로 생긴 세션 {len(result['added'])}개 (저장 파일이 낡았습니다):")
        print_panel_rows(result["added"], snapshot["probe_cache"])
        print("\n갱신하려면: /cube-cmux save")

    print_diagnostics(snapshot)


def print_restore_warning(panel, uncertain, cache):
    """복구 명령에 붙일 경고를 출력합니다."""
    if uncertain or resolution(panel) != "recorded":
        print("⚠️  이미 실행 중일 수 있고, ID가 추정이거나 오래된 기록일 수 있습니다.")
    state = cached_probe(cache, panel)
    if state == "absent":
        print("⚠️  세션 데이터가 없습니다. 재개해도 빈 세션이 열릴 수 있습니다.")
    elif state == "unknown":
        print("⚠️  세션 데이터 존재 여부를 확인하지 못했습니다.")


def cmd_restore(arg=None):
    _, _, snapshot, result = load_comparison()
    cache = snapshot["probe_cache"]
    candidates = result["missing"] + result["uncertain"]

    if not candidates:
        print("누락 또는 확인 필요 항목이 없습니다.")
        print_diagnostics(snapshot)
        return

    uncertain_ids = {index for index, _ in result["uncertain"]}

    # 번호를 지정한 경우: 확인 필요 항목도 경고와 함께 그 세션 하나만 클립보드에 담습니다
    if arg is not None:
        try:
            index = int(arg)
        except ValueError:
            print(f"번호가 아닙니다: {arg}")
            sys.exit(1)

        panel = dict(candidates).get(index)
        if panel is None:
            valid = ", ".join(str(i) for i, _ in sorted(candidates))
            print(f"[{index}]는 복구 후보가 아닙니다. 사용 가능한 번호: {valid}")
            sys.exit(1)

        command = resume_command(panel)
        print(f"[{index}] {panel['workspace']} — {panel['kind']}")
        print(f"  {command}\n")
        print_restore_warning(panel, index in uncertain_ids, cache)
        if copy_to_clipboard(command):
            print("✓ 클립보드에 복사했습니다 — 검토 후 새 패널에서 ⌘V + Enter")
        else:
            print("클립보드 복사에 실패했습니다. 위 명령어를 직접 복사해 주세요.")
        return

    # 번호가 없는 경우: 누락과 확인 필요를 나눠 목록을 출력합니다
    for key, label in (("missing", "누락"), ("uncertain", "확인 필요")):
        if result[key]:
            print(f"{label} {len(result[key])}개\n")
            for index, panel in result[key]:
                print_panel_row(index, panel, cache)
                print(f"       {resume_command(panel)}")
                print_restore_warning(panel, key == "uncertain", cache)
    print_diagnostics(snapshot)

    # 자동 복사는 후보가 하나뿐이고, 관측이 완전한 누락이며, 저장 당시 recorded일 때만 합니다
    if len(candidates) == 1:
        index, panel = candidates[0]
        if index not in uncertain_ids and resolution(panel) == "recorded":
            if copy_to_clipboard(resume_command(panel)):
                print("\n✓ 클립보드에 복사했습니다 — 새 패널에서 ⌘V + Enter")
                return

    print("\n각 명령어는 서로 다른 패널에서 실행해야 합니다.")
    print("경고를 확인한 뒤 하나씩 복사하려면: /cube-cmux restore <번호>")


def main():
    args = sys.argv[1:]
    command = args[0] if args else "status"
    if command == "list":
        cmd_list()
    elif command == "save":
        cmd_save()
    elif command == "status":
        cmd_status()
    elif command == "restore":
        cmd_restore(args[1] if len(args) > 1 else None)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
