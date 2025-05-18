# runall.py (중복 load_df 제거 최종 완성본)
import sys
from utils.cfg import cfg
from scripts.dataframe import load_df
from scripts.ext_info import extract_all_info
from scripts.mm_gen import mm_gen_main
from scripts.fst_mapper import fst_mapper_main
from scripts.fx_elab import fx_elab_main
from scripts.gen_msg import gen_msg_main
from scripts.upload import upload_main


class RunAllPipeline:
    def __init__(self):
        self.timestamp = cfg.get_timestamp()
        self.paths = cfg.get_results_path(self.timestamp)
        self.log_file = cfg.init_log_file(self.timestamp)
        self.strategy_df = None
        cfg.log(f"🚀 RunAll 시작: {self.timestamp}", self.log_file)

    def run_extract(self) -> bool:
        cfg.log("📦 1단계: Git 변경 정보 수집 시작", self.log_file)
        updated = extract_all_info()
        if not updated:
            cfg.log("🛑 변경된 파일 없음 → 전체 파이프라인 중단", self.log_file)
            return False
        cfg.log("✅ Git 정보 수집 완료", self.log_file)
        return True

    def run_strategy(self) -> bool:
        try:
            cfg.log("🧠 2단계: 전략 예측 시작", self.log_file)
            mm_gen_main()
            cfg.log("✅ 전략 예측 완료", self.log_file)
            self.strategy_df = load_df(self.paths["strategy"])
            return True
        except Exception as e:
            cfg.log(f"❌ 전략 예측 실패: {e}", self.log_file)
            return False

    def run_classify(self):
        if self.strategy_df is None or self.strategy_df.empty:
            cfg.log("⚠️ strategy_df 없음 또는 비어있음 → 분류 생략", self.log_file)
            return
        try:
            cfg.log("📊 3단계: 파일 전략 분류 시작", self.log_file)
            fst_mapper_main()
            cfg.log("✅ 파일 전략 분류 완료", self.log_file)
        except Exception as e:
            cfg.log(f"❌ 파일 전략 분류 실패: {e}", self.log_file)

    def run_explain(self):
        if self.strategy_df is None or self.strategy_df[self.strategy_df["Importance"] > 3].empty:
            cfg.log("⚠️ 설명 생성 대상 없음 → 생략", self.log_file)
            return
        try:
            cfg.log("📝 4단계: 기능 설명 생성 시작", self.log_file)
            fx_elab_main()
            cfg.log("✅ 기능 설명 완료", self.log_file)
        except Exception as e:
            cfg.log(f"❌ 기능 설명 실패: {e}", self.log_file)

    def run_commit_msg(self):
        if self.strategy_df is None or self.strategy_df[self.strategy_df["Importance"] > 3].empty:
            cfg.log("⚠️ 커밋 메시지 대상 없음 → 생략", self.log_file)
            return
        try:
            cfg.log("✉️ 5단계: 커밋 메시지 생성 시작", self.log_file)
            gen_msg_main()
            cfg.log("✅ 커밋 메시지 생성 완료", self.log_file)
        except Exception as e:
            cfg.log(f"❌ 커밋 메시지 생성 실패: {e}", self.log_file)

    def run_upload(self):
        try:
            cfg.log("☁️ 6단계: 커밋 및 업로드 시작", self.log_file)
            upload_main()
            cfg.log("✅ 커밋 및 업로드 완료", self.log_file)
        except Exception as e:
            cfg.log(f"❌ 업로드 실패: {e}", self.log_file)

    def run_all(self):
        if not self.run_extract():
            return
        if not self.run_strategy():
            return
        self.run_classify()
        self.run_explain()
        self.run_commit_msg()
        self.run_upload()
        cfg.log("🎯 전체 파이프라인 종료", self.log_file)


if __name__ == "__main__":
    runner = RunAllPipeline()
    if len(sys.argv) == 1:
        runner.run_all()
    else:
        step = sys.argv[1]
        method = getattr(runner, f"run_{step}", None)
        if callable(method):
            method()
        else:
            print(f"❌ 지원되지 않는 실행 단계: {step}")
