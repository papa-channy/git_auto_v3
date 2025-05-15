#!/bin/bash

# 📦 프로젝트 루트 기준 동적 경로 설정
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PY_PATH="$ROOT_DIR/runall.py"
STORAGE_FILE="$APPDATA/Code/storage.json"

# ⏱ 현재 timestamp 기준 로그 디렉토리 생성
TIMESTAMP=$(date +"%y%m%d_%H%M")
LOG_DIR="$ROOT_DIR/logs/$TIMESTAMP"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/trigger.log"

# 로그 기록 함수
log() {
    echo "[$(date +'%H:%M:%S')] $1" >> "$LOG_FILE"
}

log "🚀 auto.sh launched"
python "$PY_PATH"
# # VSCode 종료 감지용 상태 플래그
# was_alive=true

# # VSCode 마지막 경로 추출 함수
# get_last_vscode_dir() {
#     grep -oE '"file://[^"]+"' "$STORAGE_FILE" | head -1 | sed 's|"file://||' | sed 's|"||'
# }

# while true; do
#     sleep 10

#     if pgrep -f "Code.exe" > /dev/null; then
#         was_alive=true
#     else
#         if [ "$was_alive" = true ]; then
#             DIR=$(get_last_vscode_dir)

#             if [ -d "$DIR/.git" ]; then
#                 cd "$DIR" || exit

#                 ORIGIN=$(git config --get remote.origin.url | sed 's#.*/##' | sed 's/.git$//')
#                 NAME=$(basename "$DIR")

#                 if [ "$ORIGIN" = "$NAME" ]; then
#                     log "✅ 실행 조건 충족: $DIR → runall.py 실행"
#                     python "$PY_PATH"
#                 else
#                     log "⚠️ origin 이름 불일치 ($ORIGIN != $NAME) → skip"
#                 fi
#             else
#                 log "❌ .git 폴더 없음 → $DIR 무시됨"
#             fi

#             was_alive=false
#         fi
#     fi
# done
