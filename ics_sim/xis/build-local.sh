#!/usr/bin/env bash
#
# build-local.sh -- 보관본을 건드리지 않고 작업 사본에서 XIS(stock ISIS v2.9.1)를 빌드한다.
#
# 이 폴더(xis/)는 __dts_legacy 원본과 바이트가 같아야 SHA256SUMS.txt 로 출처를
# 검증할 수 있다.  그래서 여기서 직접 make 하지 않는다 -- *.o / isis.a / 바이너리가
# 섞이는 순간 검증이 깨진다.  대신 필요한 파일만 밖으로 복사해 거기서 빌드한다.
#
# 원본이 CRLF 라서(백업을 윈도우로 옮기며 변환된 것으로 보인다. 운영 리눅스에서는
# LF 였을 수밖에 없다 -- CRLF 인 csh 스크립트는 실행이 안 된다) 작업 사본에서는
# 줄끝을 LF 로 되돌린다.  안 하면 세 군데가 깨진다:
#   - Makefile.build : VFLAGS 의 줄이음 '\' 뒤에 \r 이 붙어 -D 매크로가 통째로 날아감
#   - isis.ini       : loadconfig.c 의 sscanf("%s %[^\n]") 가 \r 을 값에 넣어 ServerID 가 "XIS\r"
#   - *.sh, build    : #!/bin/csh^M -> bad interpreter
#
# 사용법:
#   ./build-local.sh                          # ~/xis-build 에서 빌드, ~/xis 에 설치
#   ./build-local.sh --sim 192.168.0.50:6600  # 설정에 시뮬 주소까지 넣어서
#   ./build-local.sh --prefix /opt/xis --build-dir /tmp/xb
#
# 자세한 배경: xis.md 3~4절

set -euo pipefail

ARCHIVE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$HOME/xis-build"
PREFIX="$HOME/xis"
SIM_ADDR=""
MARKER=".xis-build-dir"

die() { printf '\n[실패] %s\n' "$*" >&2; exit 1; }
say() { printf '\n== %s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --build-dir) BUILD_DIR="${2:?--build-dir 에 경로가 필요하다}"; shift 2 ;;
    --prefix)    PREFIX="${2:?--prefix 에 경로가 필요하다}";       shift 2 ;;
    --sim)       SIM_ADDR="${2:?--sim 에 IP:PORT 가 필요하다}";     shift 2 ;;
    -h|--help)   sed -n '3,21p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *)           die "모르는 인자: $1  (--help 참고)" ;;
  esac
done

[ -d "$ARCHIVE/src/server" ] || die "보관본을 찾을 수 없다: $ARCHIVE/src/server"

# ---------------------------------------------------------------- 0. 사전 점검
say "0. 도구와 라이브러리 확인"
for tool in make ar ranlib sed find; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool 이 없다.  build-essential(또는 gcc-c++ make) 설치 필요"
done
CXX_BIN="${CXX:-g++}"
command -v "$CXX_BIN" >/dev/null 2>&1 || die "$CXX_BIN 이 없다.  build-essential(또는 gcc-c++) 설치 필요"

# readline/history 헤더는 유일한 외부 의존성이다(나머지는 전부 libc).
echo '#include <readline/readline.h>
#include <readline/history.h>
int main(void){return 0;}' > /tmp/xis_dep_check.$$.cc
if ! "$CXX_BIN" -fsyntax-only /tmp/xis_dep_check.$$.cc 2>/dev/null; then
  rm -f /tmp/xis_dep_check.$$.cc
  die "readline 헤더가 없다.  libreadline-dev (Debian/Ubuntu) 또는 readline-devel (RHEL 계열) 설치 필요"
fi
rm -f /tmp/xis_dep_check.$$.cc
echo "   OK  $CXX_BIN + readline"

# ------------------------------------------------------- 1. 작업 사본 만들기
say "1. 작업 사본 만들기 -> $BUILD_DIR"
case "$BUILD_DIR" in
  "$ARCHIVE"|"$ARCHIVE"/*) die "빌드 디렉토리를 보관본 안에 두면 안 된다.  체크섬이 깨진다" ;;
esac
if [ -e "$BUILD_DIR" ] && [ ! -e "$BUILD_DIR/$MARKER" ]; then
  die "$BUILD_DIR 가 이미 있고 이 스크립트가 만든 것이 아니다.  지우거나 --build-dir 로 다른 경로를 줄 것"
fi
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
touch "$BUILD_DIR/$MARKER"

# doc/ 는 doxygen 생성물이고 그 안에만 바이너리(png/gif)가 있다.  빌드에 불필요하므로 제외.
cp -R "$ARCHIVE/src/server/." "$BUILD_DIR/"
rm -rf "$BUILD_DIR/doc"
echo "   복사한 파일 $(find "$BUILD_DIR" -type f | wc -l)개 (doc/ 제외)"

# --------------------------------------------------------- 2. 줄끝 정규화
say "2. 줄끝 CRLF -> LF"
converted=0
while IFS= read -r -d '' f; do
  # grep -I 는 바이너리를 매치하지 않는다.  만약을 위한 방어.
  if grep -Iq . "$f" 2>/dev/null; then
    sed -i 's/\r$//' "$f"
    converted=$((converted + 1))
  fi
done < <(find "$BUILD_DIR" -type f ! -name "$MARKER" -print0)
echo "   $converted개 처리"

# ------------------------------------------------- 3. Makefile 서픽스 규칙 교정
say "3. Makefile.build 의 .c.o 규칙 교정"
# 원본은  ".c.o:       isisserver.h"  인데, GNU make 는 전제조건이 붙은 서픽스
# 규칙을 서픽스 규칙으로 보지 않는다(".c.o" 라는 이름의 평범한 타겟이 된다).
# 그러면 라이브러리 오브젝트가 make 내장 규칙으로 컴파일되면서 $(VFLAGS) 가
# 빠지고, commands.c 의 콘솔 VERSION 이 헤더 기본값 0.0 / 0000-00-00 으로 굳는다.
# clean 을 먼저 하므로 헤더 의존성은 어차피 필요 없다.
if grep -qE '^\.c\.o:[[:space:]]+[^[:space:]]' "$BUILD_DIR/Makefile.build"; then
  sed -i 's/^\.c\.o:[[:space:]].*$/.c.o:/' "$BUILD_DIR/Makefile.build"
  echo "   전제조건 제거 -> 정상적인 서픽스 규칙이 됐다"
else
  echo "   교정 불필요"
fi

# ------------------------------------- 3b. 포인터를 정수 0 과 순서비교하는 곳
say "3b. interfaces.c 의 포인터/정수0 순서비교 교정"
# `if (strstr(argStr,">") > 0)` -- strstr 은 포인터를 돌려주는데 정수 0 과 `>` 로
# 비교한다.  C++ Core Issue 1512 이후 ill-formed 라 현대 g++ 은 **에러**로 낸다
# (경고가 아니라서 CFLAGS 의 -w 로도, -std=gnu++98 로도 안 넘어간다).
# 의도는 "찾았으면" 이므로 != NULL 이 의미상 정확히 같다 -- strstr 은 못 찾으면
# NULL, 찾으면 유효 포인터라 참/거짓이 동일하다.
# 2026-08-11 SSO AIC 머신(g++ 실측)에서 실제로 막힌 지점이다.
n_ptr=$(grep -cE 'strstr\(argStr,">"\)[[:space:]]*>[[:space:]]*0' "$BUILD_DIR/interfaces.c" || true)
if [ "${n_ptr:-0}" -gt 0 ]; then
  sed -i 's/strstr(argStr,">")[[:space:]]*>[[:space:]]*0/strstr(argStr,">") != NULL/g' "$BUILD_DIR/interfaces.c"
  echo "   $n_ptr 곳을 != NULL 로 교정"
else
  echo "   교정 불필요"
fi

# ---------------------------------------- 3c. serverlog.c 의 런타임 결함 두 개
say "3c. serverlog.c 런타임 결함 교정"
# 앞의 교정들과 성격이 다르다 -- 이건 컴파일은 되지만 동작이 틀린 것이다.
# 사용자 결정으로 교정한다(2026-08-11). 원본은 보관본에 그대로 남는다.
#
#  (1) open() 에 mode 인자가 없다.  O_CREAT 를 주면서 3번째 인자를 생략해
#      권한이 가변인자 쓰레기로 정해진다.  실측(SSO AIC)에서는 0666 이 나왔지만
#      빌드·머신마다 달라지고, 0 이 나오면 파일을 못 연다.
#  (2) 못 열었을 때 `isis.doLogging == isis_FALSE;` -- '=' 가 아니라 '=='.
#      로깅이 꺼지지 않아 이후 write(-1,...) 이 계속 조용히 실패한다.
#
# logMessage() 는 호출마다 날짜를 비교해 바뀌었으면 close() 후 initLog() 로
# 재오픈한다.  즉 (1)은 관측야가 바뀔 때마다 다시 일어나고, 거기서 (2)가 겹치면
# 그날 밤 로그가 통째로 사라진다.  시험용으로 계속 띄울 물건이라 고쳐 둔다.
n_log=0
if grep -q 'open(isis.logFile,(O_WRONLY|O_CREAT|O_APPEND));' "$BUILD_DIR/serverlog.c"; then
  sed -i 's/open(isis\.logFile,(O_WRONLY|O_CREAT|O_APPEND))/open(isis.logFile,(O_WRONLY|O_CREAT|O_APPEND),0644)/' "$BUILD_DIR/serverlog.c"
  n_log=$((n_log + 1))
  echo "   open() 에 mode 0644 추가"
fi
if grep -q 'isis.doLogging == isis_FALSE;' "$BUILD_DIR/serverlog.c"; then
  sed -i 's/isis\.doLogging == isis_FALSE;/isis.doLogging = isis_FALSE;/' "$BUILD_DIR/serverlog.c"
  n_log=$((n_log + 1))
  echo "   doLogging '==' -> '=' (대입으로)"
fi
[ "$n_log" -eq 0 ] && echo "   교정 불필요"

# ------------------------------------------------------------------ 4. 빌드
say "4. 빌드"
cd "$BUILD_DIR"
# -std=gnu++98 이 필요한 이유:
#   logMessage("문자열") 5곳 (commands.c:136, interfaces.c:355, utils.c:103/157/190)
#     -> 원형이 int logMessage(char *) 라 C++11 부터 에러.  GCC 11+ 는 기본이 gnu++17.
#   register 2곳 (interfaces.c:929-930) -> C++17 에서 제거된 키워드.
# LIBS 를 덮어쓰는 이유: 원본은 -I/lhome/dts/include (OSU 배치 경로, 존재하지 않음).
make -f Makefile.build clean >/dev/null
make -f Makefile.build \
  CC="$CXX_BIN -std=gnu++98" \
  AR=ar \
  LIBS="-lreadline -lhistory -lncurses" \
  COMPDATE="$(date -u +%Y-%b-%d)" \
  COMPTIME="$(date -u +%T)" \
  CONFIG="$PREFIX/Config/isis.ini" \
  DCONFIG="$PREFIX/Config/isisd.ini" \
  LOGS="$PREFIX/Logs/isis"

[ -x "$BUILD_DIR/isis" ]  || die "isis 가 만들어지지 않았다"
[ -x "$BUILD_DIR/isisd" ] || die "isisd 가 만들어지지 않았다"

# ------------------------------------------------------------------ 5. 검증
say "5. 검증"
"$BUILD_DIR/isis" -v || die "isis -v 실행 실패"

# 3번 교정이 실제로 먹었는지 바이너리에서 확인한다.  VFLAGS 가 빠졌다면
# isisserver.h 의 #ifndef 기본값 "0000-00-00" 이 commands.c 쪽에 박혀 남는다.
if command -v strings >/dev/null 2>&1; then
  if strings "$BUILD_DIR/isis" | grep -q '0000-00-00'; then
    printf '   [경고] 라이브러리 오브젝트에 VFLAGS 가 안 먹었다.\n'
    printf '          isis -v 는 정상이지만 콘솔 VERSION 은 0.0 으로 뜬다.\n'
    printf '          Makefile.build 의 .c.o 규칙을 확인할 것.\n'
  else
    echo "   OK  VFLAGS 가 라이브러리 오브젝트까지 적용됐다"
  fi
else
  echo "   (strings 가 없어 VFLAGS 확인은 건너뛴다 -- 콘솔에서 VERSION 을 쳐 볼 것)"
fi

# ------------------------------------------------------------------ 6. 설치
say "6. 설치 -> $PREFIX"
mkdir -p "$PREFIX/bin" "$PREFIX/Config" "$PREFIX/Logs"
install -m 0755 "$BUILD_DIR/isis" "$BUILD_DIR/isisd" "$PREFIX/bin/"

INI="$PREFIX/Config/isis.ini"
if [ -e "$INI" ]; then
  echo "   설정은 그대로 둔다(이미 있음): $INI"
else
  # !! 한 줄이 80 바이트를 넘으면 안 된다 -- loadconfig.c 의 CFG_BUFSIZE 가 80 이라
  #    fgets 가 줄을 자르고, 잘린 뒷도막이 다음 줄로 읽혀 설정 항목으로 파싱된다.
  #    한글 주석은 글자당 3바이트라 특히 쉽게 넘는다.  그래서 주석을 ASCII 로 쓴다.
  {
    echo "# XIS test config -- generated by build-local.sh"
    echo "# Keep every line under 80 bytes (loadconfig.c CFG_BUFSIZE)."
    echo "# Real site configs: <archive>/install/config/{ctio,saao,sso}/"
    echo ""
    echo "ServerID   XIS"
    echo "ServerPort 6660"
    echo "ServerLog  $PREFIX/Logs/isis"
    echo ""
    echo "# Log date defaults to OBSDAY (noon-to-noon local time), so the"
    echo "# filename is the observing night, not today. Uncomment for UTC:"
    echo "#LogDate UTC"
    echo ""
    echo "# Node addresses to ping at startup. MAXPRESET is 32."
    if [ -n "$SIM_ADDR" ]; then
      echo "UDPPort ${SIM_ADDR%:*} ${SIM_ADDR##*:}"
    else
      echo "#UDPPort 192.168.0.50 6600"
    fi
    echo ""
    echo "# TTYPort is only for the legacy VDOS serial link."
    echo "# See <archive>/src/server/00SerialConfig.txt for permissions."
    echo "#TTYPort /dev/ttyS0 115200"
    echo ""
    echo "Verbose"
    echo "# 'Instrument' is parsed by a buggy branch in loadconfig.c and ends"
    echo "# up holding the previous entry's value. Harmless, nothing reads it."
    echo "Instrument KMTTEST"
  } > "$INI"
  echo "   설정 생성: $INI"
fi

# 직접 쓴 설정이든 생성한 것이든, 80 바이트 넘는 줄이 있으면 조용히 오작동한다.
long=$(awk 'length($0) >= 80 {printf "        %d행 (%d바이트): %.50s...\n", NR, length($0), $0}' "$INI")
if [ -n "$long" ]; then
  printf '   [경고] 80 바이트 이상인 줄이 있다 -- loadconfig.c 가 잘라 읽어\n'
  printf '          뒷도막을 설정 항목으로 오인한다. 줄을 줄일 것:\n%s\n' "$long"
fi

# ------------------------------------------------------------------ 안내
cat <<EOF

== 완료

  실행:  $PREFIX/bin/isis -f$INI

         '-f' 와 경로 사이에 공백을 넣으면 안 된다 -- main.c 가
         sscanf(*argv,"f%s",...) 로 읽어서 공백을 주면 죽는다.
         대화형이 기본이라 TTY 가 필요하다.  ssh 로 띄울 거면 tmux 안에서.

  확인:  콘솔에 VERSION  -> 2.9.1 이어야 한다 (2.7.3 이면 은퇴 분기를 빌드한 것)
                  INFO     -> "Preset UDP Ports: n configured of 32 max"
                  HOSTS    -> 등록된 노드 테이블

  시뮬:  ics_sim 을 bind_host = 0.0.0.0 으로 띄운 뒤 XIS 콘솔에서
                  UDPPING <시뮬IP> <시뮬포트>
         그리고 HOSTS 에 ICS + {K,M,T,N}.IC + {K,M,T,N}.CB 9개가 다 뜨면 성공.

         !! 레거시 ICS/IC 가 살아 있는 *운영* XIS 에는 절대 등록하지 말 것.
            clients.c 의 updateHosts() 가 같은 노드 ID 로 온 메시지의 주소로
            테이블을 무조건 덮어쓴다(충돌 검사 없음). 시뮬이 9개 ID 로 PING 하는
            순간 그 라우팅을 가로채고, 레거시가 응답하면 도로 빼앗겨 관측 명령이
            메시지 단위로 갈리는 플래핑이 된다. 레거시를 정지한 뒤에 하거나,
            이 스크립트로 띄운 시험용 인스턴스에서만 할 것. -> xis.md 7절

  로그:  $PREFIX/Logs/isis.<날짜>.log
         serverlog.c:46 이 open() 을 mode 인자 없이 부른다.  첫 실행 후
         ls -l 로 권한을 확인하고 이상하면 chmod 644 할 것.

EOF
