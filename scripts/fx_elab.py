from pathlib import Path
from scripts.dataframe import load_df, save_df
from utils.cfg import cfg
from scripts.llm_mng import LLMManager
from scripts.ext_info import to_safe_filename
import pandas as pd

def extract_keywords_code(filepath: Path) -> str:
    keywords = ("def ", "return ", "class ", "self", "@", "from ", "logger")
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
        return "\n".join([line for line in lines if any(kw in line for kw in keywords)])
    except Exception:
        return ""

def extract_readme_summary(readme_path: Path) -> str:
    try:
        content = readme_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        summary, capture = [], False
        for line in lines:
            if line.startswith("# "): capture = True
            elif line.startswith("## ") and capture: break
            if capture: summary.append(line)
        return "\n".join(summary).strip() if summary else content.split("\n\n")[0]
    except Exception:
        return ""

def fx_elab_main():
    timestamp = cfg.get_timestamp()
    paths = cfg.get_results_path(timestamp)
    log_file = cfg.init_log_file(timestamp)

    repo_df = load_df(paths["repo"])
    info_df = load_df(paths["info"])
    strategy_df = load_df(paths["strategy"])

    root_path = Path(repo_df["Root path"].iloc[0])
    readme_path = root_path / "README.md"
    folder_lines, file_lines = cfg.build_llm_file_structure(root_path)
    tree_structure = "\n".join(folder_lines + file_lines)

    prompts, tags, meta_rows = [], [], []

    for _, row in strategy_df.iterrows():
        file = row["File"]
        id_ = row["id"]
        name4save = row["name4save"]
        save_path = row["save_path"]
        fx_in_path = Path(save_path[1])
        fx_out_path = Path(save_path[2])

        info_row = info_df[info_df["file"] == file]
        if info_row.empty:
            cfg.log(f"[fx_elab] ⚠️ {file} 경로 정보 없음", log_file)
            continue

        file_path = Path(info_row["path"].iloc[0]) / to_safe_filename(file)
        strategy = row["File strategy"]

        try:
            main_content = (
                file_path.read_text(encoding="utf-8")
                if strategy == "full_pass"
                else extract_keywords_code(file_path)
            )
        except Exception:
            main_content = ""
            cfg.log(f"[fx_elab] ❌ {file} 파일 읽기 실패", log_file)

        related_info = []
        for related in row.get("Most Related Files", []):
            match = info_df[info_df["file"] == related]
            if match.empty:
                cfg.log(f"[fx_elab] ⚠️ 관련 파일 없음: {related}", log_file)
                continue
            r_path = Path(match["path"].iloc[0]) / to_safe_filename(related)
            r_code = extract_keywords_code(r_path)
            r_commit = match["5 latest commit"].iloc[0][:1]
            related_info.append(f"{related}:\n{r_code}\n최근 커밋: {r_commit[0] if r_commit else ''}\n")
        if not related_info:
            related_info.append("관련 파일 없음")

        try:
            commit_lines = "\n".join(
                info_row["5 latest commit"].iloc[0][:row["Num of extract file"]]
            )
        except Exception:
            commit_lines = ""
            cfg.log(f"[fx_elab] ⚠️ 커밋 정보 누락: {file}", log_file)

        readme_flag = row.get("Readme strategy", [False, "x"])
        if readme_flag[0]:
            try:
                readme_content = (
                    extract_readme_summary(readme_path)
                    if readme_flag[1] == "summary"
                    else readme_path.read_text(encoding="utf-8")
                )
            except Exception:
                readme_content = ""
        else:
            readme_content = ""

        prompt = f"""
📌 요청 목적:
아래 스크립트의 주요 기능과 로직을 300 tokens 내외로 요약해주세요.
레포 전체 구조에서의 역할과 연계성을 포함해주세요.

📎 분석 FILE: {file}
📎 기능 유형: {row['Component Type']}
📎 중요도: {row['Importance']}

📎 메인 스크립트 내용:
{main_content}

📎 최근 커밋 메시지:
{commit_lines}

📎 관련 스크립트 요약:
{"".join(related_info)}

📎 폴더 구조:
{tree_structure}

📎 README 요약:
{readme_content}
반드시 한국어로 작성해주세요.
""".strip()

        fx_in_path.parent.mkdir(parents=True, exist_ok=True)
        fx_in_path.write_text(prompt, encoding="utf-8")

        prompts.append(prompt)
        tags.append(id_)
        meta_rows.append({
            "id": id_,
            "name4save": name4save,
            "save_path": [str(fx_in_path), str(fx_out_path)]
        })

    if not prompts:
        cfg.log("[fx_elab] ❌ 생성된 프롬프트 없음", log_file)
        return

    df_for_call = pd.DataFrame(meta_rows)

    with LLMManager("explain", repo_df, df_for_call=df_for_call) as llm:
        results = llm.call_all(prompts, tags)
        for result, row in zip(results, meta_rows):
            fx_out_path = Path(row["save_path"][1])
            fx_out_path.write_text(result, encoding="utf-8")

        llm.save_all()
