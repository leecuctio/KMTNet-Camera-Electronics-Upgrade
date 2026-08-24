#!/usr/bin/env bash
#
# build-local.sh -- 저장소를 건드리지 않고 작업 사본에서 TCS Agent(pctcs)를 빌드한다.
#
# 여기서 직접 make 하면 *.o 와 바이너리가 소스 옆에 생겨 git status 가 더러워진다
# (루트 .gitignore 에 *.o/*.a 규칙이 없다).  그래서 필요한 파일만 밖으로 복사해
# 거기서 빌드한다 -- ics_sim/xis/build-local.sh 와 같은 방침이다.
#
# 원 배포본은 2014~2018년 CentOS 계열 + 그 시절 g++/readline 으로 빌드됐다.
# 12년치 차이로 그냥은 넘어가지 않는 것이 여섯 가지 있고 전부 여기서 처리한다.
# 근거는 tcsagent_report.md 12절.
#
# 사용법:
#   ./build-local.sh                       # ~/AIC 아래에 빌드 + 설정 생성
#   ./build-local.sh --site kmtnc          # CTIO 설정으로
#   ./build-local.sh --root /opt/aic
#   ./build-local.sh --no-config           # ini 는 건드리지 않기
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HOME/AIC"
SITE="kmtna"          # kmtna=SSO  kmtnc=CTIO  kmtns=SAAO  kmtnt=TestBed
MAKE_CONFIG=1

die() { printf '\n[실패] %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --root)      ROOT="${2:?--root 에 경로가 필요하다}"; shift 2 ;;
    --site)      SITE="${2:?--site 에 kmtna|kmtnc|kmtns|kmtnt 가 필요하다}"; shift 2 ;;
    --no-config) MAKE_CONFIG=0; shift ;;
    -h|--help)   sed -n '3,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *)           die "모르는 인자: $1  (--help 참고)" ;;
  esac
done

SRC_AGENT="$REPO/TCSAgent.latest/KMTNet"
SRC_ISIS="$REPO/__reference/ISISclient"
[ -d "$SRC_AGENT" ] || die "소스를 찾을 수 없다: $SRC_AGENT"
[ -d "$SRC_ISIS" ]  || die "ISISclient 를 찾을 수 없다: $SRC_ISIS"
[ -f "$SRC_AGENT/ini/pctcs.$SITE.ini" ] || die "사이트 ini 가 없다: pctcs.$SITE.ini"

BUILD="$ROOT/build"
CONFIG="$ROOT/Config"
LOGS="$ROOT/Logs/TC"
ISISDIR="$BUILD/ISISclient"
AGENTDIR="$BUILD/TCSAgent"

case "$BUILD" in
  "$REPO"|"$REPO"/*) die "빌드 디렉토리를 저장소 안에 두면 안 된다: $BUILD" ;;
esac

# ------------------------------------------------------------- 0. 사전 점검
say "0. 도구와 라이브러리 확인"
for tool in make ar ranlib sed; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool 이 없다.  build-essential 설치 필요"
done
CXX_BIN="${CXX:-g++}"
command -v "$CXX_BIN" >/dev/null 2>&1 || die "$CXX_BIN 이 없다.  build-essential 설치 필요"

printf '#include <readline/readline.h>\n#include <readline/history.h>\nint main(void){return 0;}\n' \
  > "/tmp/tcs_dep_check.$$.cc"
if ! "$CXX_BIN" -fsyntax-only "/tmp/tcs_dep_check.$$.cc" 2>/dev/null; then
  rm -f "/tmp/tcs_dep_check.$$.cc"
  die "readline 헤더가 없다.  libreadline-dev (또는 readline-devel) 설치 필요"
fi
rm -f "/tmp/tcs_dep_check.$$.cc"
echo "   OK  $CXX_BIN + readline"

mkdir -p "$BUILD" "$CONFIG" "$LOGS"

# --------------------------------------------- 1. ISISclient (libisis.a 재빌드)
#
# 커밋된 libisis.a 는 2014년 non-PIC 빌드라 요즘 기본값인 PIE 실행파일에 못 섞인다
#   relocation R_X86_64_32 against '.rodata' can not be used when making a PIE object
# 소스가 있으므로 재빌드한다.  그러면 아래 두 가지가 드러난다.
say "1. ISISclient 재빌드 -> $ISISDIR"
rm -rf "$ISISDIR"
cp -R "$SRC_ISIS" "$ISISDIR"
cd "$ISISDIR"
rm -f libisis.a ./*.o

# (a) 리터럴 -> char* 가 C++11 부터 에러.  -std=gnu++98 로 회피
sed -i 's|^CC *=.*|CC          = /usr/bin/g++ -std=gnu++98|' Makefile

# (b) strstr 의 char* 를 정수 0 과 순서비교 -- C++ Core Issue 1512 이후 ill-formed.
#     XIS 의 interfaces.c 에 있던 것과 글자 그대로 같은 줄이다(공통 조상 코드)
sed -i 's|strstr(addrhdr,">")>0|strstr(addrhdr,">") != NULL|' isismessage.c

# (c) ISODate() 버퍼 부족 -- "CCYY-MM-DDThh:mm:ss" 19자+NUL 을 str[11] 에 쓴다.
#     2004년에 UTCDate()(날짜 전용, 11 로 정확)를 복사해 시각을 덧붙이면서
#     버퍼를 안 키운 것.  static 이라 .bss 를 침범하고 기동 시 1회만 불려
#     20년 넘게 조용했다.  tcsagent_report.md 12.4 ①
sed -i '/^\*ISODate(void)/,/^}/ s|static char str\[11\];|static char str[24];|' isisutils.c

make clean >/dev/null
make "COMPDATE=$(date +%Y-%b-%d)" "COMPTIME=$(date +%T)" >/dev/null 2>&1 \
  || { make "COMPDATE=$(date +%Y-%b-%d)" "COMPTIME=$(date +%T)"; die "libisis.a 빌드 실패"; }
[ -f libisis.a ] || die "libisis.a 가 만들어지지 않았다"
echo "   OK  libisis.a ($(stat -c%s libisis.a) bytes)"

# ------------------------------------------------------------ 2. TCS Agent
say "2. TCS Agent 빌드 -> $AGENTDIR"
rm -rf "$AGENTDIR"
cp -R "$SRC_AGENT" "$AGENTDIR"
cd "$AGENTDIR"
rm -f pctcs ./*.o

# (a) ISISLIB 이 존재하지 않는 OSU 배치 경로(/home/dts/ISIS/client)를 가리킨다
sed -i -e "s|^ISISLIB *=.*|ISISLIB     = $ISISDIR|" \
       -e 's|^CC *=.*|CC          = /usr/bin/g++ -std=gnu++98|' Makefile

# (b) 포인터/정수0 순서비교 + glibc 2.27(2018)에서 삭제된 pow10()
sed -i -e 's|strstr(args,"-c")>0|strstr(args,"-c") != NULL|' \
       -e 's|pow10(nDP)|pow(10.0,(double)nDP)|' commands.c

# (c) readline 초기화 전 rl_refresh_line() -- 빌드는 되고 실행이 즉사한다.
#     _msgout()/_vmsgout() 이 배너부터 이걸 부르는데 rl_callback_handler_install()
#     은 이벤트 루프 직전에야 돈다.  readline 8.x 가 NULL 인 rl_prompt 에
#     strrchr 을 걸면서 SIGSEGV.  지우지 말고 가드를 씌운다 -- 초기화 후에는
#     원래 동작(비동기 출력 뒤 프롬프트 다시 그리기)이 필요하다.
sed -i 's|rl_refresh_line(0,0);|if(rl_prompt) rl_refresh_line(0,0);|g' \
       main.c commands.c comsoft.c

# (d) 로그 경로가 소스에 박혀 있다.  원본 줄은 주석으로 남긴다.
#
#     DEFAULT_LOGFILE 은 loadconfig.c 가 ini 의 LOGFILE 로 덮어쓰는 **기본값**
#     이므로 설치 자리를 가리켜도 된다 -- ini 로 바꿀 수 있다.
#
#     TEMP_LOGFILE 은 다르다.  main.c:263 이 ini 를 **읽기 전에** 열어
#     (기동 배너를 담는 자리다) ini 로는 원리상 못 고친다.  그래서
#     설치 루트가 아니라 **/tmp 로 고정**한다 -- 설치 자리를 옮겨도
#     재빌드가 필요 없다.  이 파일은 수 초만 살고 loadconfig 뒤에 ini 의
#     LOGFILE 자리로 mv 되므로(main.c:321) **최종 로그 위치는 여전히 ini 가
#     정한다.**  운영자 요청 2026-08-24.
#     (sed 의 & 는 '매치 전체'다.  큰따옴표 안에서 \& 로 쓰면 리터럴 & 가 되어
#      원본 줄이 주석으로 남지 않으니 그냥 & 로 둘 것)
sed -i \
 -e "s|^#define DEFAULT_LOGFILE\( *\)\"/data/Logs/TC/tc\".*$|//&\n#define DEFAULT_LOGFILE\1\"$LOGS/tc\"|" \
 -e "s|^#define TEMP_LOGFILE\( *\)\"/data/Logs/TC/tc.temp.log\"$|//&\n#define TEMP_LOGFILE\1\"/tmp/pctcs.temp.log\"|" \
 pctcs.h

make clean >/dev/null
if ! make "COMPDATE=$(date +%Y-%b-%d)" "COMPTIME=$(date +%T)" > /tmp/tcs_build.$$.log 2>&1; then
  grep -E "error:|Error [0-9]" /tmp/tcs_build.$$.log | head -20
  die "pctcs 빌드 실패 (전체 로그: /tmp/tcs_build.$$.log)"
fi
rm -f ./*.o
[ -x pctcs ] || die "pctcs 가 만들어지지 않았다"
echo "   OK  pctcs ($(stat -c%s pctcs) bytes)"
echo "   남은 경고: main.c 의 sprintf 오버플로 6곳 -- VERBOSE on 일 때만 발현한다"
echo "              (tcsagent_report.md 12.4 ②, 미교정)"

# --------------------------------------------------------------- 3. 설정
if [ "$MAKE_CONFIG" = 1 ]; then
  say "3. 설정 생성 -> $CONFIG/pctcs.ini  (site=$SITE)"
  if [ -e "$CONFIG/pctcs.ini" ]; then
    echo "   이미 있다 -- 건드리지 않는다.  다시 만들려면 지우고 실행할 것"
  else
    sed -e 's|^ISISHost .*|ISISHost  127.0.0.1|' \
        -e 's|^TCS_Host .*|TCS_Host   127.0.0.1 (bench)|' \
        -e 's|^AUX_Host .*|AUX_Host   127.0.0.1 (bench)|' \
        -e "s|^LOGFILE .*|LOGFILE  $LOGS/tc|" \
        -e "s|^CATFILE .*|CATFILE  $AGENTDIR/catalog/pctcs.cat|" \
        "$SRC_AGENT/ini/pctcs.$SITE.ini" > "$CONFIG/pctcs.ini"
    echo "   생성됨"
  fi
  cat <<EOF

   !! TCS_Host / AUX_Host 를 127.0.0.1 로 두었다.
      사이트 기본값(예: 192.168.15.60)은 실제 필터/셔터/포커서/돔셔터를
      제어하는 AUX 컴퓨터와 Telcom 이다.  시험용 프로세스를 거기 붙이지 말 것.
      Telcom/AUX 시뮬레이터를 같은 머신에 올리면 이 값 그대로 링크가 UP 이 된다.
EOF
fi

say "완료"
cat <<EOF
  실행:  $AGENTDIR/pctcs $CONFIG/pctcs.ini

  기대: '> Event Logging started successfully' 와 TC% 프롬프트.
        Telcom/AUX 가 없으면 두 링크는 DOWN 으로 뜬다 -- 정상이다.
  확인: XIS 콘솔 HOSTS 에 TC 가 127.0.0.1:6606 으로 올라온다.
EOF
