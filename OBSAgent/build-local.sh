#!/usr/bin/env bash
#
# build-local.sh -- 저장소를 건드리지 않고 작업 사본에서 OBS Agent(obstool)를 빌드한다.
#
# 방침과 걸림돌 대부분은 TCSAgent/build-local.sh 와 같다 -- OBSAgent 가 TCSAgent
# 코드베이스를 복사해 출발했기 때문에 결함도 같은 줄에 그대로 있다.
# OBSAgent 고유는 셋이다:
#   - hiredis 를 직접 빌드해야 하고, 그것도 정적(.a)으로 링크해야 한다
#   - libcurl 이 추가로 필요하다
#   - 하드코딩 경로가 다섯 곳이다 (TCSAgent 는 둘)
# 근거는 obsagent_report.md 12절.
#
# 사용법:
#   ./build-local.sh                       # ~/AIC 아래에 빌드 + 설정 생성
#   ./build-local.sh --site kmtnc
#   ./build-local.sh --root /opt/aic --no-config
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HOME/AIC"
SITE="kmtna"          # kmtna=SSO  kmtnc=CTIO  kmtns=SAAO
MAKE_CONFIG=1

die() { printf '\n[실패] %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --root)      ROOT="${2:?--root 에 경로가 필요하다}"; shift 2 ;;
    --site)      SITE="${2:?--site 에 kmtna|kmtnc|kmtns 가 필요하다}"; shift 2 ;;
    --no-config) MAKE_CONFIG=0; shift ;;
    -h|--help)   sed -n '3,18p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *)           die "모르는 인자: $1  (--help 참고)" ;;
  esac
done

SRC="$REPO/OBSAgent.latest"
[ -d "$SRC/KMTObs" ]     || die "소스를 찾을 수 없다: $SRC/KMTObs"
[ -d "$SRC/hiredis" ]    || die "hiredis 를 찾을 수 없다: $SRC/hiredis"
[ -d "$SRC/ISISclient" ] || die "ISISclient 를 찾을 수 없다: $SRC/ISISclient"
[ -f "$SRC/KMTObs/ini/obstool.$SITE.ini" ] || die "사이트 ini 가 없다: obstool.$SITE.ini"

BUILD="$ROOT/build"
CONFIG="$ROOT/Config"
LOGS="$ROOT/Logs"
ISISDIR="$BUILD/ISISclient"
OBSDIR="$BUILD/OBSAgent"
BIN="$ROOT/bin"

case "$BUILD" in
  "$REPO"|"$REPO"/*) die "빌드 디렉토리를 저장소 안에 두면 안 된다: $BUILD" ;;
esac

# ------------------------------------------------------------- 0. 사전 점검
say "0. 도구와 라이브러리 확인"
for tool in make ar ranlib sed cc; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool 이 없다.  build-essential 설치 필요"
done
CXX_BIN="${CXX:-g++}"
command -v "$CXX_BIN" >/dev/null 2>&1 || die "$CXX_BIN 이 없다.  build-essential 설치 필요"

check_header() {  # <헤더> <패키지 안내>
  printf '#include <%s>\nint main(void){return 0;}\n' "$1" > "/tmp/obs_dep.$$.c"
  if ! cc -fsyntax-only "/tmp/obs_dep.$$.c" 2>/dev/null; then
    rm -f "/tmp/obs_dep.$$.c"; die "$1 이 없다.  $2 설치 필요"
  fi
  rm -f "/tmp/obs_dep.$$.c"
}
check_header readline/readline.h "libreadline-dev"
check_header curl/curl.h        "libcurl4-openssl-dev"   # v1.0.0 부터 -lcurl
echo "   OK  $CXX_BIN + readline + curl"

mkdir -p "$BUILD" "$CONFIG" "$LOGS/OBS" "$ROOT/bin"

# --------------------------------------------- 1. ISISclient (libisis.a 재빌드)
# 커밋된 .a 는 2014년 non-PIC 라 PIE 실행파일에 못 섞인다:
#   relocation R_X86_64_32 against '.rodata' can not be used when making a PIE object
# **그래서 항상 다시 만든다.**
#
# 종전에는 $ISISDIR/libisis.a 가 있으면 건너뛰었다("TCSAgent 쪽 사본과 바이트
# 동일하므로").  그런데 그게 참인지 확인하지 않았다 -- 옛 세션이나 다른 경로에서
# 흘러든 .a 를 그대로 물고 위 PIE 오류로 죽는다 (2026-08-24 실측: 설치 루트를
# 옮긴 뒤 정확히 이 증상).  $BUILD/ISISclient 는 이 스크립트와 TCSAgent 가
# **공유**하는 자리라 누가 어떤 플래그로 만들었는지 추적할 수 없으므로, 몇 초
# 아끼자고 그 위험을 남길 이유가 없다.  TCSAgent 는 처음부터 항상 재빌드였다.
say "1. ISISclient 재빌드 -> $ISISDIR"
rm -rf "$ISISDIR"
cp -R "$SRC/ISISclient" "$ISISDIR"
cd "$ISISDIR"
rm -f libisis.a ./*.o
sed -i 's|^CC *=.*|CC          = /usr/bin/g++ -std=gnu++98|' Makefile
sed -i 's|strstr(addrhdr,">")>0|strstr(addrhdr,">") != NULL|' isismessage.c
sed -i '/^\*ISODate(void)/,/^}/ s|static char str\[11\];|static char str[24];|' isisutils.c
make clean >/dev/null
make "COMPDATE=$(date +%Y-%b-%d)" "COMPTIME=$(date +%T)" >/dev/null 2>&1 \
  || die "libisis.a 빌드 실패"
[ -f libisis.a ] || die "libisis.a 가 만들어지지 않았다"
echo "   OK  libisis.a ($(stat -c%s libisis.a) bytes)"

# ----------------------------------------------------------------- 2. hiredis
# Makefile 의 all: 은 공유 라이브러리만 만든다.  -lhiredis 로 링크하면 링커가
# .so 를 우선 잡고, 그 .so 는 표준 경로에 없어 실행이 안 된다:
#   error while loading shared libraries: libhiredis.so.0.11
# static: 타겟으로 .a 를 따로 만들고, Makefile 에서 경로로 직접 지정한다.
say "2. hiredis 빌드 (정적) -> $OBSDIR/hiredis"
rm -rf "$OBSDIR"
mkdir -p "$OBSDIR"
cp -R "$SRC/KMTObs"  "$OBSDIR/KMTObs"
cp -R "$SRC/hiredis" "$OBSDIR/hiredis"
cd "$OBSDIR/hiredis"
make clean >/dev/null 2>&1 || true
make >/dev/null 2>&1 || die "hiredis 빌드 실패"
make static >/dev/null 2>&1 || die "hiredis 정적 라이브러리 생성 실패"
[ -f libhiredis.a ] || die "libhiredis.a 가 만들어지지 않았다"
echo "   OK  libhiredis.a"

# ------------------------------------------------------------- 3. OBS Agent
say "3. OBS Agent 빌드 -> $OBSDIR/KMTObs"
cd "$OBSDIR/KMTObs"
rm -f obstool ./*.o

# (a) TCSAgent 와 같은 줄의 같은 결함 두 가지
sed -i 's|strstr(args,"-c")>0|strstr(args,"-c") != NULL|' commands.c
sed -i 's|pow10(nDP)|pow(10.0,(double)nDP)|' calculation.c

# (b) readline 초기화 전 호출.  rl_callback_handler_install() 은 main.c:432 인데
#     배너·설정 로딩의 _msgout() 호출이 그 앞에 37개 있다.
sed -i 's|rl_refresh_line(0,0);|if(rl_prompt) rl_refresh_line(0,0);|g' main.c commands.c

# (c) 하드코딩 경로 5곳 -- ObsStatus.txt + 로그 4종.  원본 줄은 주석으로 남긴다.
#     (& 는 sed 에서 '매치 전체'다.  큰따옴표 안에서 \& 로 쓰면 리터럴 & 가 되어
#      원본 줄이 주석으로 남지 않는다)
sed -i "s|^\( *\)#define \([A-Z_]*\)\( *\)\"/data/Logs/\([^\"]*\)\"\(.*\)$|//&\n\1#define \2\3\"$LOGS/\4\"|" obstool.h

# (d-2) 위 치환은 /data/Logs/* 를 **전부** $LOGS 아래로 옮긴다.  그중 둘은
#       성질이 달라 뒤에서 다시 손본다 (운영자 요청 2026-08-24).
#
#   TEMP_*LOGFILE 3종 -- main.c:190~192 가 LoadConfig(214)보다 **먼저** 연다.
#     ini 로는 원리상 못 고치므로 설치 루트에 두면 루트를 옮길 때마다 재빌드가
#     필요하다.  /tmp 로 고정하면 그 의존이 사라진다.  이 파일들은 수 초만
#     살고 ini 의 LOGFILE 자리로 mv 되므로(main.c:252/285) **최종 로그 위치는
#     여전히 ini 가 정한다.**
sed -i "s|^\( *\)#define \(TEMP_[A-Z]*LOGFILE\)\( *\)\"[^\"]*/\([^/\"]*\)\"|\1#define \2\3\"/tmp/\4\"|" obstool.h
grep -q '#define TEMP_EVENTLOGFILE  *"/tmp/' obstool.h \
  || die "TEMP_*LOGFILE 을 /tmp 로 돌리는 패치가 먹지 않았다 (obstool.h 형식 변경?)"

#   DEFAULT_OBSSTAT -- ObsStatus.txt 경로.  ini 키가 **아예 없어서** 컴파일
#     상수로만 정해졌다.  ini 키 OBSSTATFILE 을 신설하고 기본값은 종전 상수로
#     둔다 -- ini 에 키가 없으면 거동이 지금과 완전히 같다.
sed -i 's|^extern char cmsg\[STRLEN_CMSG\];\(.*\)$|&\nextern char obsStatFile[256];  // ObsStatus.txt path (ini: OBSSTATFILE)|' obstool.h
sed -i 's|^char cmsg\[STRLEN_CMSG\];\(.*\)$|char cmsg[STRLEN_CMSG];\1\nchar obsStatFile[256] = DEFAULT_OBSSTAT;  // overridden by ini OBSSTATFILE|' main.c
sed -i 's|WriteObsStatus(DEFAULT_OBSSTAT)|WriteObsStatus(obsStatFile)|g' main.c
sed -i '/else if(strcasecmp(keyword, "LOGFILE")==0)/i\
      else if(strcasecmp(keyword, "OBSSTATFILE")==0) {\
        GetArg(inbuf, 2, argbuf);\
        strcpy(obsStatFile, argbuf);\
      }\
' loadconfig.c
grep -q 'extern char obsStatFile' obstool.h \
  && grep -q 'char obsStatFile\[256\] = DEFAULT_OBSSTAT' main.c \
  && grep -q 'WriteObsStatus(obsStatFile)' main.c \
  && grep -q '"OBSSTATFILE"' loadconfig.c \
  || die "OBSSTATFILE ini 키 패치가 먹지 않았다 (소스 형식 변경?)"

# (d) Makefile -- 컴파일러 표준, ISISLIB, 그리고 hiredis 를 .a 경로로 직접 링크
sed -i -e 's|^ *CC *=.*| CC          = /usr/bin/g++ -std=gnu++98|' \
       -e "s|^ *ISISLIB *=.*| ISISLIB    = $ISISDIR|" \
       -e 's|-lhiredis|$(HIREDIS)/libhiredis.a|g' Makefile

make clean >/dev/null
if ! make "COMPDATE=$(date +%Y-%b-%d)" "COMPTIME=$(date +%T)" > /tmp/obs_build.$$.log 2>&1; then
  grep -E "error:|Error [0-9]" /tmp/obs_build.$$.log | head -20
  die "obstool 빌드 실패 (전체 로그: /tmp/obs_build.$$.log)"
fi
rm -f ./*.o
[ -x obstool ] || die "obstool 이 만들어지지 않았다"
if ldd obstool 2>/dev/null | grep -qi hiredis; then
  die "hiredis 가 동적으로 링크됐다 -- 실행 시 라이브러리를 못 찾는다"
fi
echo "   OK  obstool ($(stat -c%s obstool) bytes), hiredis 정적 링크 확인"

# --------------------------------------------------------------- 4. 설정
if [ "$MAKE_CONFIG" = 1 ]; then
  say "4. 설정 생성 -> $CONFIG/obstool.ini  (site=$SITE)"
  if [ -e "$CONFIG/obstool.ini" ]; then
    echo "   이미 있다 -- 건드리지 않는다.  다시 만들려면 지우고 실행할 것"
  else
    sed -e 's|^ISISHost .*|ISISHost  127.0.0.1|' \
        -e "s|^LOGFILE .*|LOGFILE  $LOGS/OBS/obs|" \
        "$SRC/KMTObs/ini/obstool.$SITE.ini" > "$CONFIG/obstool.ini"
    # ObsStatus.txt -- 종전에는 컴파일 상수뿐이었다 (위 d-2).  ini 로 적어 두면
    # 설치 자리를 옮길 때 이 줄만 고치면 되고 재빌드가 필요 없다.
    grep -qi '^OBSSTATFILE' "$CONFIG/obstool.ini" \
      || printf 'OBSSTATFILE  %s\n' "$LOGS/ObsStatus.txt" >> "$CONFIG/obstool.ini"
    echo "   생성됨"
  fi
fi


# ------------------------------------------------------------------ 5. 설치
#
# **bin/ 까지 넣는다** (운영자 요청 2026-08-24).  종전에는 build/ 에만 만들고
# "여기서 실행하라" 고 안내했는데, 사람이 손으로 bin/ 에 복사해 두면 그 사본이
# **개명·판올림 때 조용히 낡은 채로 남는다** -- 2026-08-24 에 설치 루트를 옮긴 뒤
# bin/ 의 옛 판이 옛 경로를 물고 있어 실제로 걸렸다.  XIS 는 처음부터 bin/ 에
# 설치했으므로 이제 셋이 같다.
say "5. 설치 -> $BIN"
mkdir -p "$BIN"
install -m 0755 "$OBSDIR/KMTObs/obstool" "$BIN/" \
  || die "obstool 설치 실패 -- 돌고 있으면 'Text file busy' 다.  내리고 다시 실행할 것"
echo "   OK  $BIN/obstool"

say "완료"
cat <<EOF
  실행:  $BIN/obstool $CONFIG/obstool.ini

  !! 포트 6650 은 ics_sim/tools/xis_probe.py 도 쓴다.  띄우기 전에 프로브를 끌 것.

  기대: OBS% 프롬프트.  Redis/웹릴레이 접속 실패 경고는 정상이다
        (3회 연속 실패하면 스스로 모니터링을 끈다).
  확인: OBS% status  ->  ICS 응답
        OBS% kstatus ->  K.IC 응답  (신규 ics 의 9노드 등록이 실전에서 동작한다는 뜻)
        watch -n 1 cat $LOGS/ObsStatus.txt   # CamStatus 실시간 관찰
EOF
