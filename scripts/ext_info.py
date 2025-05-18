import subprocess
import pandas as pd
import tiktoken
from pathlib import Path
from datetime import datetime
from dateutil.parser import parse
from collections import Counter
import uuid

from scripts.dataframe import init_info_df, init_strategy_df, save_df
from utils.cfg import cfg


def run_git(args: list[str], cwd: Path = Path.cwd()) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip()

def get_changed_files(log_file) -> list[str]:
    output = run_git(["git", "status", "--porcelain"])
    lines = output.splitlines()
    changed = []
    allowed_exts = cfg.get_allowed_extensions(log_func=lambda msg: cfg.log(msg, log_file))
    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))

    for line in lines:
        if not line.strip():
            continue
        status, path = line[:2].strip(), line[3:].strip()
        full_path = root / path
        if status in {"M", "A", "??"}:
            if not full_path.exists():
                cfg.log(f"[ext_info] ⚠️ Git status에 있으나 파일 없음 → 제외: {path}", log_file)
                continue
            if full_path.suffix not in allowed_exts:
                cfg.log(f"[ext_info] ⏭️ 제외된 확장자: {path}", log_file)
                continue
            changed.append(path)
    return changed

def extract_readme_token_and_strategy() -> tuple:
    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))
    readme_path = root / "README.md"
    try:
        enc = tiktoken.encoding_for_model("gpt-4")
    except:
        enc = tiktoken.get_encoding("cl100k_base")

    if not readme_path.exists():
        return 0, [False, "x"]

    content = readme_path.read_text(encoding="utf-8")
    token_len = len(enc.encode(content))
    if token_len < 30:
        return token_len, [False, "x"]
    elif token_len <= 150:
        return token_len, [True, "full"]
    else:
        return token_len, [True, "summary"]

def count_filetypes(file_list: list[str]) -> dict:
    return dict(Counter([Path(f).suffix for f in file_list if "." in f]))

def decide_commit_count(third_date: datetime | None) -> int:
    if not third_date:
        return 3
    now = cfg.get_now("commit")
    days = (now - third_date).days
    if days > 10:
        return 5
    elif days > 5:
        return 4
    return 3

def extract_repo_info(readme_token: int, log_file) -> pd.DataFrame:
    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))
    branches = run_git(["git", "branch", "--format=%(refname:short)"]).splitlines()
    head = run_git(["git", "symbolic-ref", "--short", "HEAD"])
    default_branch = next((b for b in ["main", "master"] if b in branches), branches[0] if branches else None)
    contributors = run_git(["git", "shortlog", "-sne"]).splitlines()
    recent_commit_count = len(run_git(["git", "log", "--since=14 days ago", "--oneline"]).splitlines())
    changed_files = get_changed_files(log_file)
    diff_stat = run_git(["git", "diff", "--stat", "--"] + changed_files)

    return pd.DataFrame([{
        "Repo": root.name,
        "Main branch": default_branch,
        "Branch list": branches,
        "Current branch": head,
        "Contributors": len(contributors),
        "Root path": str(root),
        "Commit frequency": recent_commit_count,
        "File count": count_filetypes(changed_files),
        "Diff list": changed_files,
        "Diff stat": diff_stat,
        "Readme token": readme_token
    }])

def extract_info_and_strategy(files: list[str], readme_strategy: list, log_file, paths: dict) -> tuple:
    info_df = init_info_df(files)
    strategy_df = init_strategy_df(files)

    try:
        enc = tiktoken.encoding_for_model("gpt-4")
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")

    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))

    # 1️⃣ UUID 및 파일명 초기값 삽입
    for i, f in enumerate(files):
        file_name = Path(f).name
        info_df.at[i, "id"] = str(uuid.uuid4())
        strategy_df.at[i, "id"] = info_df.at[i, "id"]
        info_df.at[i, "file"] = file_name
        strategy_df.at[i, "File"] = file_name

    # 2️⃣ 중복 없는 name4save 생성
    used = {}
    for i, name in info_df["file"].items():
        base = Path(name).stem + Path(name).suffix
        if base not in used:
            used[base] = 0
            name4save = base
        else:
            used[base] += 1
            name4save = f"{Path(name).stem}_{used[base]}{Path(name).suffix}"
        info_df.at[i, "name4save"] = name4save
        strategy_df.at[i, "name4save"] = name4save

    assert info_df["name4save"].isnull().sum() == 0, "❌ name4save 결측 있음"

    # 3️⃣ save_path 리스트 채움
    for i, name in info_df["name4save"].items():
        info_df.at[i, "save_path"] = [
            str(paths["diff"] / f"diff_{name}.txt"),
            str(paths["explain_in"] / f"{name}.txt"),
            str(paths["explain_out"] / f"{name}.txt"),
            str(paths["mk_msg_in"] / f"{name}.txt"),
            str(paths["mk_msg_out"] / f"{name}.txt"),
        ]
        strategy_df.at[i, "save_path"] = info_df.at[i, "save_path"]

    # 4️⃣ 상세 정보 채움 + diff 저장
    for i, f in enumerate(files):
        full_path = root / f
        folder_path = full_path.parent
        name4save = info_df.at[i, "name4save"]

        try:
            text = full_path.read_text(encoding="utf-8")
        except Exception as e:
            text = ""
            cfg.log(f"[ext_info] ❌ {f} 파일 읽기 실패: {e}", log_file)

        diff = run_git(["git", "diff", "--", str(f)])
        diff_token = len(enc.encode(diff))
        diff_path = paths["diff"] / f"diff_{Path(name4save).stem}.txt" # diff 저장 경로는 str(paths["diff"] / f"diff_{namesave}.txt"),
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(diff, encoding="utf-8")

        date_strs = run_git(["git", "log", "--pretty=format:%ad", "--date=iso", "--", str(f)]).splitlines()
        try:
            times = [parse(d).strftime("%y/%m/%d %H:%M") for d in date_strs if d.strip()]
        except Exception as e:
            times = [cfg.get_now("commit").strftime("%y/%m/%d %H:%M")]
            cfg.log(f"[ext_info] ❌ {f} 커밋 시간 파싱 실패: {e}", log_file)

        try:
            third_date = (
                parse(date_strs[2]) if len(date_strs) >= 3
                else parse(date_strs[-1]) if date_strs else cfg.get_now("commit")
            )
        except Exception as e:
            third_date = cfg.get_now("commit")
            cfg.log(f"[ext_info] ❌ {f} third_date 파싱 실패: {e}", log_file)

        msg_count = decide_commit_count(third_date)
        recent_msgs = run_git([
            "git", "log", "--since=" + third_date.strftime('%Y-%m-%d'),
            "--pretty=format:%s", "--", str(f)
        ]).splitlines()
        recent_msgs = (recent_msgs + [""] * 5)[:5]

        info_df.at[i, "path"] = str(folder_path)
        info_df.at[i, "file token"] = len(enc.encode(text))
        info_df.at[i, "diff var name"] = f"diff_{Path(name4save).stem}"
        info_df.at[i, "diff token"] = diff_token
        info_df.at[i, "Files in folder"] = len([p for p in folder_path.iterdir() if p.is_file()])
        info_df.at[i, "last commit time"] = times
        info_df.at[i, "5 latest commit"] = recent_msgs

        strategy_df.at[i, "Num of extract file"] = msg_count
        strategy_df.at[i, "Readme strategy"] = readme_strategy

    return info_df, strategy_df

def to_safe_filename(filename: str) -> str:
    """
    OS-safe한 파일 이름 반환
    (예: 슬래시, 백슬래시, 공백 등 제거 또는 대체)
    """
    return filename.replace("/", "_").replace("\\", "_").replace(" ", "_")

# 전체 통합 실행
def extract_all_info() -> bool:
    timestamp = cfg.get_timestamp()
    paths = cfg.get_results_path(timestamp)
    log_file = cfg.init_log_file(timestamp)
    readme_token, readme_strategy = extract_readme_token_and_strategy()
    repo_df = extract_repo_info(readme_token, log_file)
    files = repo_df.iloc[0]["Diff list"]

    if not files:
        cfg.log("⚠️ 변경된 파일이 없습니다. info/strategy 생략됨.", log_file)
        info_df = init_info_df([])
        strategy_df = init_strategy_df([])
        updated = False
    else:
        info_df, strategy_df = extract_info_and_strategy(files, readme_strategy, log_file, paths)
        updated = True

    save_df(repo_df, paths["repo"])
    save_df(info_df, paths["info"])
    save_df(strategy_df, paths["strategy"])
    cfg.log("✅ 정보 수집 완료", log_file)

    return updated
