#!/usr/bin/env python3
"""cmux 패널의 에이전트 세션을 저장하고, 복원되지 않은 세션의 재개 명령어를 안내합니다.

cmux가 자체 세션 파일(session-com.cmuxterm.app.json)에 기록해 둔 패널 정보를 읽어
에이전트 세션의 재개 명령어를 파일로 남깁니다. cmux 복원이 실패했을 때 저장 목록과
현재 열린 패널을 대조해 누락된 세션만 골라냅니다.

저장 파일은 `cmux-sessions-<YYMMDD-HHMM>.md` 형식이며, `status`와 `restore`는
가장 최근 파일을 자동으로 선택합니다. 복구가 끝난 파일은 삭제해도 무방합니다.

표준 라이브러리만 사용하며 cmux와 각 에이전트의 세션 저장소를 읽기 전용으로
조회합니다.

Usage:
    cmux_session.py list              현재 열린 패널 목록 출력 (저장하지 않음)
    cmux_session.py save              현재 패널을 새 저장 파일로 기록
    cmux_session.py status            최근 저장 파일과 현재 패널을 대조 (기본값)
    cmux_session.py restore           누락 세션 목록 출력 (1개면 클립보드 복사)
    cmux_session.py restore <번호>    해당 세션의 명령어를 클립보드에 복사

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
OPENCODE_DB = os.path.expanduser("~/.local/share/opencode/opencode.db")
ANTIGRAVITY_CONVERSATIONS = os.path.expanduser("~/.gemini/antigravity-cli/conversations")


# --- cmux 세션 파일 읽기 ---------------------------------------------------


def read_panels(path=SESSION_FILE):
    """cmux 세션 파일에서 에이전트가 붙은 패널 목록을 뽑아냅니다."""
    if not os.path.exists(path):
        return None

    # cmux가 파일을 쓰는 도중 종료되면 JSON이 잘려 있을 수 있습니다.
    # 트레이스백 대신 None을 돌려주고 호출부에서 안내합니다.
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    panels = []
    for window in data.get("windows", []):
        workspaces = window.get("tabManager", {}).get("workspaces", [])
        for ws in workspaces:
            title = (
                ws.get("customTitle")
                or os.path.basename(ws.get("currentDirectory", ""))
                or "(무제)"
            )
            for panel in ws.get("panels", []):
                terminal = panel.get("terminal") or {}
                agent = terminal.get("agent") or {}
                session_id = agent.get("sessionId")
                kind = agent.get("kind")
                if not session_id or not kind:
                    continue
                launch_args = (agent.get("launchCommand") or {}).get("arguments") or []
                if kind in ("claude", "opencode"):
                    launch_args = []
                panels.append(
                    {
                        "workspace": title,
                        "kind": kind,
                        "sessionId": session_id,
                        "cwd": agent.get("workingDirectory") or panel.get("directory"),
                        "panelTitle": panel.get("title", ""),
                        # cmux가 기록해 둔 실행 인자입니다.
                        # 재개 방법을 모르는 에이전트는 이걸로 명령어를 복원합니다.
                        "launchArgs": launch_args,
                    }
                )
    return panels


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


def session_data_exists(panel):
    """세션 데이터(대화 기록)가 아직 디스크에 남아 있는지 확인합니다."""
    session_id = panel["sessionId"]

    if panel["kind"] == "claude":
        if panel["cwd"]:
            # cmux의 cwd -> claude 프로젝트 디렉토리 슬러그 ('/'와 '.'이 '-'로 바뀝니다)
            slug = panel["cwd"].replace("/", "-").replace(".", "-")
            if os.path.exists(os.path.join(CLAUDE_PROJECTS, slug, f"{session_id}.jsonl")):
                return True
        # 슬러그 규칙이 어긋날 수 있으므로 전체 프로젝트에서 한 번 더 찾습니다
        return bool(glob.glob(f"{CLAUDE_PROJECTS}/*/{session_id}.jsonl"))

    if panel["kind"] == "opencode":
        # opencode는 세션을 SQLite DB에 보관합니다.
        # storage/ 디렉토리에는 session_diff 등 부산물만 남으므로 DB를 직접 조회합니다.
        if not os.path.exists(OPENCODE_DB):
            return False
        try:
            connection = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
            try:
                found = connection.execute(
                    "SELECT 1 FROM session WHERE id = ? LIMIT 1", (session_id,)
                ).fetchone()
            finally:
                connection.close()
            return found is not None
        except sqlite3.Error:
            # 스키마가 바뀌었거나 DB를 열 수 없는 경우 판정을 보류합니다
            return True

    if panel["kind"] == "antigravity":
        # 대화는 conversations/<id>.db에 저장됩니다 (구버전은 .pb).
        return bool(glob.glob(f"{ANTIGRAVITY_CONVERSATIONS}/{session_id}.*"))

    # 저장 위치를 모르는 에이전트는 판정을 보류합니다.
    # 데이터가 있는데 '!'를 붙이면 잘못된 경고가 되기 때문입니다.
    return True


# --- 저장 파일 읽고 쓰기 ---------------------------------------------------


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


def write_save_file(panels):
    """사람이 읽는 목록과 restore가 파싱할 JSON을 한 파일에 담습니다."""
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
        "cmux 복원이 실패하면 새 패널을 열고 아래 명령어를 붙여넣으면 됩니다.",
        "복구가 끝나면 이 파일은 삭제해도 됩니다.",
        "",
    ]

    for index, panel in enumerate(panels, start=1):
        exists = "O" if session_data_exists(panel) else "X (세션 데이터 없음)"
        lines += [
            f"## [{index}] {panel['workspace']} — {panel['kind']}",
            "",
            f"- 패널 제목: {panel['panelTitle']}",
            f"- 작업 경로: {panel['cwd']}",
            f"- 세션 데이터: {exists}",
            "",
            "```sh",
            resume_command(panel),
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
    """저장 파일의 JSON 블록을 되읽습니다."""
    try:
        with open(path) as f:
            content = f.read()
    except OSError:
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
    except json.JSONDecodeError:
        return None

    if not isinstance(saved, dict):
        return None
    if not isinstance(saved.get("savedAt"), str) or not isinstance(saved.get("panels"), list):
        return None
    for panel in saved["panels"]:
        if not isinstance(panel, dict):
            return None
        if not all(
            isinstance(panel.get(key), str) and panel[key]
            for key in ("workspace", "kind", "sessionId")
        ):
            return None
        if "cwd" not in panel or not isinstance(panel["cwd"], (str, type(None))):
            return None
        if not isinstance(panel.get("launchArgs", []), list):
            return None
    return saved


def copy_to_clipboard(text):
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# --- 명령 --------------------------------------------------------------------


def require_current_panels():
    panels = read_panels()
    if panels is None:
        print(f"cmux 세션 파일을 읽을 수 없습니다 (없거나 손상됨): {SESSION_FILE}")
        sys.exit(1)
    return panels


def print_panel_rows(panels):
    """패널 목록을 한 줄씩 출력합니다. save와 list가 같은 형식을 씁니다."""
    for index, panel in enumerate(panels, start=1):
        # 세션 데이터가 없으면 '!'로 표시합니다
        mark = " " if session_data_exists(panel) else "!"
        print(
            f"  [{index}]{mark} {panel['workspace']:16} {panel['kind']:9} {panel['sessionId'][:8]}"
        )


def cmd_list():
    panels = require_current_panels()
    if not panels:
        print("에이전트가 붙은 패널이 없습니다.")
        return

    print(f"현재 열린 세션 {len(panels)}개\n")
    print_panel_rows(panels)
    print("\n저장하려면: /cube-cmux save")


def cmd_save():
    panels = require_current_panels()
    if not panels:
        print("에이전트가 붙은 패널이 없습니다. 저장할 세션이 없습니다.")
        return

    previous = latest_save_file()
    path = write_save_file(panels)

    print(f"저장 완료: {path}")
    print(f"세션 {len(panels)}개\n")
    print_panel_rows(panels)

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


def diff_saved_vs_current():
    """저장 목록과 현재 패널을 대조해 (경로, 저장 데이터, 누락, 신규)를 돌려줍니다."""
    path, saved = load_saved()
    current = require_current_panels()
    current_ids = {p["sessionId"] for p in current}
    saved_ids = {p["sessionId"] for p in saved["panels"]}

    # 번호는 저장 시점의 순서를 유지합니다. 복구가 진행돼도 번호가 밀리지 않습니다.
    missing = [
        (index, panel)
        for index, panel in enumerate(saved["panels"], start=1)
        if panel["sessionId"] not in current_ids
    ]
    added = [p for p in current if p["sessionId"] not in saved_ids]
    return path, saved, missing, added


def cmd_status():
    path, saved, missing, added = diff_saved_vs_current()
    total = len(saved["panels"])

    print(f"저장 파일: {os.path.basename(path)} ({saved['savedAt']})")
    print(f"저장 {total}개 / 복원 {total - len(missing)}개 / 누락 {len(missing)}개\n")

    if missing:
        print("누락:")
        for index, panel in missing:
            print(
                f"  [{index}] {panel['workspace']:16} {panel['kind']:9} {panel['sessionId'][:8]}"
            )
        print("\n복구하려면: /cube-cmux restore")
    else:
        print("누락 없습니다. 저장된 세션이 모두 열려 있습니다.")

    if added:
        print(f"\n저장 이후 새로 생긴 세션 {len(added)}개 (저장 파일이 낡았습니다):")
        for panel in added:
            print(f"  + {panel['workspace']:16} {panel['kind']:9} {panel['sessionId'][:8]}")
        print("\n갱신하려면: /cube-cmux save")


def cmd_restore(arg=None):
    _, _, missing, _ = diff_saved_vs_current()

    if not missing:
        print("누락된 세션이 없습니다. 복구할 것이 없습니다.")
        return

    by_index = {index: panel for index, panel in missing}

    # 번호를 지정한 경우: 그 세션 하나만 클립보드에 담습니다
    if arg is not None:
        try:
            index = int(arg)
        except ValueError:
            print(f"번호가 아닙니다: {arg}")
            sys.exit(1)

        panel = by_index.get(index)
        if panel is None:
            valid = ", ".join(str(i) for i, _ in missing)
            print(f"[{index}]는 누락 목록에 없습니다. 사용 가능한 번호: {valid}")
            sys.exit(1)

        command = resume_command(panel)
        print(f"[{index}] {panel['workspace']} — {panel['kind']}")
        print(f"  {command}\n")
        if not session_data_exists(panel):
            print("⚠️  세션 데이터가 없습니다. 재개해도 빈 세션이 열릴 수 있습니다.\n")
        if copy_to_clipboard(command):
            print("✓ 클립보드에 복사했습니다 — 새 패널에서 ⌘V + Enter")
        else:
            print("클립보드 복사에 실패했습니다. 위 명령어를 직접 복사해 주세요.")
        return

    # 번호가 없는 경우: 목록을 출력합니다. 하나뿐이면 바로 복사합니다.
    print(f"누락 {len(missing)}개\n")
    for index, panel in missing:
        mark = " " if session_data_exists(panel) else "!"
        print(
            f"  [{index}]{mark} {panel['workspace']:16} {panel['kind']:9} {panel['sessionId'][:8]}"
        )
        print(f"       {resume_command(panel)}")
    print()

    if len(missing) == 1:
        index, panel = missing[0]
        if copy_to_clipboard(resume_command(panel)):
            print("✓ 클립보드에 복사했습니다 — 새 패널에서 ⌘V + Enter")
            return

    print("각 명령어는 서로 다른 패널에서 실행해야 합니다.")
    print("하나씩 클립보드에 담으려면: /cube-cmux restore <번호>")


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
