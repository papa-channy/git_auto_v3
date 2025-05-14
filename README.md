# git_auto_v3
## ✅ 자동 실행 설정 (최초 1회만)

이 프로젝트는 VSCode가 꺼질 때 자동 실행되도록 구성되어 있습니다.  
아래 명령어를 **관리자 권한 CMD**에서 한 번만 실행해 주세요:

```md
schtasks /Create /SC ONLOGON /TN GitAutoWatcher ^
/TR "\"C:\Program Files\Git\bin\bash.exe\" --login -i \"C:\Users\Admin\Desktop\git_auto_v3\auto.sh\"" ^
/F