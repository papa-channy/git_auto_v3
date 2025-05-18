from pathlib import Path
from scripts.dataframe import load_df
from scripts.ext_info import to_safe_filename
from utils.cfg import cfg
from scripts.llm_mng import LLMManager
import pandas as pd

def select_prompt_template(length: int, importance: int) -> str:
    if length >= 500 or importance >= 8:
        return "internal_detail"
    elif length >= 200:
        return "internal"
    else:
        return "solo_detail"

def gen_msg_main():
    timestamp = cfg.get_timestamp()
    paths = cfg.get_results_path(timestamp)
    log_file = cfg.init_log_file(timestamp)

    repo_df = load_df(paths["repo"])
    info_df = load_df(paths["info"])
    strategy_df = load_df(paths["strategy"])

    root_path = Path(repo_df["Root path"].iloc[0])
    folder_lines, file_lines = cfg.build_llm_file_structure(root_path)
    tree_txt = "\n".join(folder_lines + file_lines)

    prompts, tags, meta_rows = [], [], []

    lang = "ko"
    for _, row in strategy_df.iterrows():
        if row.get("Importance", 0) <= 3:
            continue

        file = row["File"]
        id_ = row["id"]
        name4save = row["name4save"]
        save_path = row["save_path"]
        prompt_in_path = Path(save_path[3])  # mk_msg_in
        prompt_out_path = Path(save_path[4])  # mk_msg_out
        safe_file = to_safe_filename(file)

        info_row = info_df[info_df["file"] == file]
        if info_row.empty:
            cfg.log(f"[gen_msg] ⚠️ {file} 경로 정보 없음", log_file)
            continue

        file_path = Path(info_row["path"].iloc[0]) / safe_file
        fx_path = Path(save_path[2])  # explain_out
        diff_path = Path(save_path[0])  # diff

        try:
            fx_summary = fx_path.read_text(encoding="utf-8")
        except Exception:
            fx_summary = ""
            cfg.log(f"[gen_msg] ❌ {file} 기능 요약 파일 읽기 실패", log_file)

        try:
            diff_txt = diff_path.read_text(encoding="utf-8")
        except Exception:
            diff_txt = ""
            cfg.log(f"[gen_msg] ❌ {file} diff 파일 읽기 실패", log_file)

        strategy = row["File strategy"]
        try:
            script_txt = (
                file_path.read_text(encoding="utf-8")
                if strategy == "full_pass"
                else "\n".join([
                    l for l in file_path.read_text(encoding="utf-8").splitlines()
                    if any(k in l for k in ["def ", "return ", "class ", "self", "@", "from ", "logger"])
                ])
            )
        except Exception:
            script_txt = ""
            cfg.log(f"[gen_msg] ❌ {file} 코드 읽기 실패", log_file)

        try:
            commit_list = info_row["5 latest commit"].iloc[0]
            commit_summary = "\n".join(commit_list[:row["Num of extract file"]])
        except Exception:
            commit_summary = ""
            cfg.log(f"[gen_msg] ⚠️ {file} 커밋 요약 추출 실패", log_file)

        length = row.get("Recommended length", 300)
        importance = row.get("Importance", 5)
        style = select_prompt_template(length, importance)
        template_path = Path(f"prompt/{lang}/{style}.txt")
        if not template_path.exists():
            cfg.log(f"[gen_msg] ❌ 템플릿 없음: {template_path}", log_file)
            continue

        try:
            base_prompt = template_path.read_text(encoding="utf-8")
        except Exception:
            cfg.log(f"[gen_msg] ❌ 템플릿 읽기 실패: {template_path}", log_file)
            continue

        full_prompt = base_prompt.replace("{change}", f"""
📘 기능 요약:
{fx_summary}

📂 폴더 구조:
{tree_txt}

📄 변경된 스크립트 주요 내용:
{script_txt}

📌 최근 커밋 메시지:
{commit_summary}

🧾 변경 사항(diff):
{diff_txt}
""").strip()

        prompt_in_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_in_path.write_text(full_prompt, encoding="utf-8")

        prompts.append(full_prompt)
        tags.append(id_)
        meta_rows.append({
            "id": id_,
            "name4save": name4save,
            "save_path": [str(prompt_in_path), str(prompt_out_path)]
        })

    if not prompts:
        cfg.log("[gen_msg] ❌ 생성된 프롬프트 없음", log_file)
        return

    df_for_call = pd.DataFrame(meta_rows)

    with LLMManager("mk_msg", repo_df, df_for_call=df_for_call) as llm:
        results = llm.call_all(prompts, tags)
        for result, row in zip(results, meta_rows):
            out_path = Path(row["save_path"][1])
            out_path.write_text(result, encoding="utf-8")

        llm.save_all()
