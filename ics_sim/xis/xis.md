# XIS — 레거시 메시지 허브 보관본과 신규 `ics` 연동 노트

> **이 폴더는 무엇인가.** KMTNet 레거시 관측 시스템의 메시지 허브 **XIS** 의 소스코드·운영 설정·기동 스크립트·실행파일을 원본에서 뽑아 한곳에 모아 둔 보관소다. 신규 `ics` 가 붙어야 할 상대가 바로 이 프로그램이므로, 조사할 때마다 `__dts_legacy` 를 다시 뒤지지 않도록 별도로 떼어 놨다.
>
> 파일 목록·출처·체크섬은 [MANIFEST.md](MANIFEST.md), 무결성 검증은 [SHA256SUMS.txt](SHA256SUMS.txt).

작성 2026-08-05 · 원본 백업 시점 2019-03-26 · 보관 원본 162 파일 / 1.5 MB

---

## 1. XIS 가 뭔가

**ISIS** (*Integrated Science Instrument Server*, R. Pogge / OSU Astronomy) 는 ICIMACS(IMPv2.5) 프로토콜을 쓰는 노드들 사이에서 메시지를 중계하는 경량 허브다. ANSI C 로 짜였고 UDP 소켓과 시리얼 포트를 동시에 다루며, GNU readline 기반 콘솔을 제공한다.

KMTNet 배포본에서는 이 허브가 `ServerID XIS` 로 기동된다. **`XIS` 는 프로그램 이름이 아니라 노드 ID다** — 그래서 런타임 로그가 `XIS runtime log (re)started at UTC ...`, `K.IC>XIS PONG` 처럼 찍힌다.

프로토콜과 노드 구성 전반은 [`../../ics_legacy/ics_legacy_report.md`](../../ics_legacy/ics_legacy_report.md) 1~2절에 정리돼 있다. 이 문서는 **허브 프로그램 자체**만 다룬다.

## 2. 폴더 구성

```
xis/
├── xis.md              ← 이 문서 (+ 부록 A: XIS 노드 등록 논의 전 과정)
├── MANIFEST.md         ← 파일 목록 · 출처 · 사이트 간 동일성
├── SHA256SUMS.txt      ← 보관 원본 162개 파일 전체 체크섬
├── build-local.sh      ← 작업 사본을 만들어 빌드·설치 (4.1절)
├── src/                ★ 운영 중인 허브 소스 (ISIS v2.9.1, 3사이트 동일)
│   ├── server/           허브 서버 — main/interfaces/messages/clients/commands/…
│   ├── client/           libisis 클라이언트 라이브러리
│   ├── relay/            isisrelay — IC 머신의 UDP↔시리얼 중계기
│   ├── doc/              ICIMACS 프로토콜 정의 · ISIS 명령 세트
│   └── config/           배포 시점 .ini 템플릿
├── install/
│   ├── config/{ctio,saao,sso}/isis.ini    ★ 사이트별 운영 설정 실물
│   └── scripts/                            기동 · 정지 · 점검 스크립트
├── tools/isisPerl/     isisCmd · execISIS — IMPv2 명령 주입 도구 (연동 시험용)
└── branches/
    └── xisis-2.7.3/    은퇴한 XISIS 분기 소스 + 실행파일 2종 + 사이트 델타
```

## 3. 실제로 도는 것은 XISIS 가 아니라 stock ISIS v2.9.1 이다

원본 백업에는 허브로 보이는 트리가 **셋** 있다. 어느 것이 운영본인지가 이번 정리의 핵심 쟁점이었다.

| 트리 | 산출 바이너리 | 버전 | 정체 |
|---|---|---|---|
| `ISIS/` | `isis` (+`isisd`, +`isisrelay`) | **2.9.1** | **운영본.** `ServerID XIS` 로 기동된다 |
| `EXEC_ISIS/` | `xisis` | 2.7.3 | Jerry Mason(OSU ISL) 의 KMTN 전용 분기, 2014-02 ~ 2014-08. **은퇴** |
| `ISIS_V1/` | `isis` | 2.7.3 | 구버전 백업 |

이름만 보면 `EXEC_ISIS`(XISIS) 가 "XIS" 같지만, **운영본은 stock `ISIS/` v2.9.1 이다.** 근거 여섯 가지:

1. **기동 스크립트.** `bin/KMTN_Startup_ICS` 가 3개 사이트 전부 `xterm -e "/home/dts/ISIS/server/isis" &` 를 실행한다. 헤더 주석은 *2014 Oct 13 [rwp/osu] — "launches the MODS-style ISIS server as XIS, and uses the isisrelay comm configuration"*. 그 위에 남은 *"August 21, 2014: Decided to run XISIS instead of ISIS"* 는 **두 달 만에 뒤집힌 이전 결정**이다.
2. **설정·로그 경로가 맞물린다.** `ISIS/server/build` 는 기본 설정 `/lhome/dts/Config/isis.ini`, 로그 `/lhome/data/Logs/ISIS/isis` 로 컴파일한다. 운영 설정 `Config/isis.ini` 의 `ServerLog` 가 정확히 그 경로다. `EXEC_ISIS/server/build` 는 `xisis.ini` / `Logs/XISIS/xisis` 를 가리키는데, **`Config/xisis.ini` 는 `OLD/`·`Version1/` 에만 남아 있다** — 은퇴한 설정이다.
3. **보드레이트.** 운영 설정은 `TTYPort /dev/ttyS0 115200` 이다. 속도 인자를 파싱하는 코드(`loadconfig.c` 의 `getArg(valStr,2,…)`)와 `B115200` 으로 매핑하는 코드(`interfaces.c`)는 **v2.9.1 에만 있다.** v2.7.3 은 `B9600` 하드코딩이라 이 설정을 처리하지 못한다.
4. **ini 주석과 헤더 상수가 일치한다.** 운영 `isis.ini` 는 *"max 16"*(시리얼) · *"max 32"*(preset) 라고 적혀 있고, `ISIS/server/isisserver.h` 가 `MAXSERIAL 16` · `MAXPRESET 32` 다. `EXEC_ISIS` 쪽 헤더는 **8 / 8** 이다.
5. **프로세스 이름.** `stopisis`·`chkisis` 가 `ps -C isis` 로 프로세스를 찾는다. v2.9.1 의 링크 산출물 이름이 `isis` 이고, v2.7.3 은 `xisis` 라 이 스크립트에 걸리지 않는다.
6. **바이너리 날짜.** 보관된 `xisis` 실행파일은 2014-02-19 · 2014-07-31 빌드로, **둘 다 2014-10-13 의 전환보다 앞선다.**

> **한계.** 백업 시점은 2019-03-26 이고 로그는 2025년까지 있다. 그 사이에 다시 바뀌었을 가능성까지 배제하지는 못한다. 실물에서 1분이면 확정된다 → 7절.

## 4. 그래서 "설치파일" 은 어디까지 확보됐나

| 구성요소 | 확보 여부 |
|---|---|
| 운영본 **소스** (v2.9.1) | ✅ `src/` — 서버 · 클라이언트 라이브러리 · relay · 문서 전부 |
| 운영본 **빌드 정의** | ✅ `src/server/Makefile.build` · `build` |
| **사이트별 운영 설정** | ✅ `install/config/{ctio,saao,sso}/isis.ini` |
| **기동/정지/점검 스크립트** | ✅ `install/scripts/` |
| **연동 시험 도구** | ✅ `tools/isisPerl/` |
| 운영본 **실행 바이너리** (`isis` v2.9.1) | ❌ **백업에 없다** — 원본 백업이 소스·설정 위주로 선별돼 있다 |
| 은퇴 분기 실행 바이너리 (`xisis` v2.7.3) | ✅ `branches/xisis-2.7.3/server/{xisis.last, old.xisis}` |

**운영 바이너리가 없어도 실질적 문제는 없다.** 소스와 빌드 정의가 온전하므로 재빌드가 가능하다. 외부 의존성은 `readline`/`history` 헤더 하나뿐이고(나머지는 전부 libc), 링크에 `ncurses` 가 붙는다.

### 4.1 빌드는 `build-local.sh` 로 — 이 폴더 안에서 하지 말 것

```bash
./build-local.sh --sim 192.168.14.50:6600
```

기본값은 `~/xis-build` 에서 빌드해 `~/xis` 에 설치한다. `--build-dir` · `--prefix` · `--sim` 으로 바꾸고, `--help` 로 요약을 본다.

> ⚠️ **`cd src/server && ./build` 를 직접 하면 안 된다.** `*.o` · `isis.a` · 바이너리가 보관본 안에 생겨 [SHA256SUMS.txt](SHA256SUMS.txt) 검증이 깨지고, `make clean` 이 원본 옆에서 돈다. 스크립트는 필요한 파일만 밖으로 복사해 거기서 빌드한다.

### 4.2 현대 툴체인에서 걸리는 것 네 가지

원 배포본은 GCC 4.4.7 (RHEL/CentOS 6, x86-64) 로 빌드됐다. 그 사이에 바뀐 것들이라 **그냥은 넘어가지 않는다.** `build-local.sh` 가 넷 다 처리한다.

> **2026-08-11 실측 완료 — Ubuntu 24.04 LTS / g++ 13.3.0 (SSO AIC 리눅스).** 실제로 빌드해 `isis`·`isisd` 가 나왔고 `./isis -v` 가 `isis version 2.9.1 (2026-Aug-11 …)` 을 찍었다.
>
> ①②③ 은 정적 분석으로 미리 잡았고, **④ 는 실제 컴파일에서만 드러났다.** 라이브러리 오브젝트 컴파일 줄에 `-DISIS_VERSION='"2.9.1"'` 이 붙은 것과 `-v` 가 `0.0` 이 아닌 것으로 ③ 의 교정이 먹었다는 것도 실측 확인됐다.
>
> 원 배포본은 GCC 4.4.7 (2012, RHEL/CentOS 6) 이었으므로 **툴체인 12년치를 건너뛴 것**이다. 걸림돌 넷이 나온 이유가 여기 있다 — 그중 둘(②④)은 그 사이에 **경고가 에러로 승격**된 항목이다.

| # | 문제 | 증상 | 스크립트의 처리 |
|---|---|---|---|
| 1 | **원본이 CRLF** (보관 167 파일 중 144개) | `Makefile.build` 의 `VFLAGS` 줄이음 `\` 뒤에 `\r` 이 붙어 **`-D` 매크로가 통째로 날아간다.** `isis.ini` 는 `loadconfig.c` 의 `sscanf("%s %[^\n]")` 가 `\r` 을 값에 넣어 **`ServerID` 가 `"XIS\r"`** 이 된다. `build`·`startisis` 는 `#!/bin/csh^M` | 작업 사본에서만 LF 로 되돌린다 |
| 2 | **`logMessage("문자열")` 5곳** (`commands.c:136` · `interfaces.c:355` · `utils.c:103,157,190`) + **`register` 2곳** (`interfaces.c:929-930`) | 원형이 `int logMessage(char *)` 라 리터럴 전달이 **C++11 부터 에러**. GCC 11+ 기본이 `gnu++17` | `CC="g++ -std=gnu++98"` |
| 3 | **`.c.o:` 서픽스 규칙에 전제조건이 붙어 있다** (`.c.o: isisserver.h`) | GNU make 는 전제조건이 있는 서픽스 규칙을 서픽스 규칙으로 보지 않는다 → 라이브러리 오브젝트가 내장 규칙으로 컴파일되며 **`$(VFLAGS)` 가 빠진다.** `isis -v` 는 멀쩡한데 콘솔 `VERSION` 만 `0.0`/`0000-00-00` 으로 뜨는 헷갈리는 증상 | 전제조건을 떼어 정상 서픽스 규칙으로 만들고, 빌드 후 바이너리에 `0000-00-00` 이 남았는지로 **실제로 먹었는지 검증**한다 |
| 4 | **포인터를 정수 0 과 순서비교** — `if (strstr(argStr,">") > 0)` 2곳 (`interfaces.c:518,748`) | `strstr` 이 돌려주는 `char*` 를 `>` 로 `0` 과 비교한다. C++ Core Issue 1512 이후 ill-formed 라 **에러**다 — 경고가 아니라서 `-w` 로도 `-std=gnu++98` 로도 안 넘어간다. **정적 분석으로는 예측 못 하고 실제 컴파일에서 드러났다** | 의미가 같은 `!= NULL` 로 바꾼다(`strstr` 은 못 찾으면 NULL, 찾으면 유효 포인터라 참/거짓 동일) |

> `main.c` 와 `isisd.c` 는 이미 `(char *)"PING"` 식으로 캐스팅돼 있다 — 과거에 g++ 로 옮기며 **일부만** 고쳐 둔 상태고, 라이브러리 쪽 5곳이 남았다.
> `Makefile.build` 의 `LIBS` 에 있는 `-I$(INCDIR)`(`/lhome/dts/include`)는 OSU 배치 경로라 존재하지 않는다. 스크립트가 `LIBS` 를 덮어써 뺀다.

### 4.3 `serverlog.c` 의 런타임 결함 두 개 — 빌드 사본에서 교정

4.2 는 **컴파일이 안 되는 것**이었다. 이 둘은 성격이 다르다 — 컴파일도 되고 평소엔 돌지만 **동작이 틀렸다.** 첫 실물 기동(2026-08-11)에서 로그 파일 권한이 `-rw-rw-rw-` 로 나온 것을 계기로 찾았고, 사용자 결정으로 빌드 사본에서 교정한다. 원본은 보관본에 그대로 남는다.

```c
// serverlog.c:46 -- O_CREAT 를 주면서 mode 인자를 생략했다
isis.logFD = open(isis.logFile,(O_WRONLY|O_CREAT|O_APPEND));

// serverlog.c:51 -- '=' 가 아니라 '=='. 대입이 아니라 결과를 버리는 비교다
isis.doLogging == isis_FALSE;
```

**① mode 없는 `open()`** — 새 로그 파일의 권한이 가변인자 쓰레기로 정해진다. SSO AIC 실측에서는 `0666`(누구나 쓰기 가능)이 나왔지만 **빌드·머신마다 달라지고, 0 이 나오면 파일을 못 연다.**

**② 실패해도 로깅이 안 꺼진다** — `==` 라서 `doLogging` 은 그대로다. 이후 `write(-1, …)` 이 계속 실패하는데 반환값을 확인하지 않아 **조용히** 아무것도 안 남는다. `-w` 가 `-Wunused-value` 경고까지 막아서 이 오타가 살아남았다.

**둘이 겹치는 지점이 문제다.** `logMessage()` 는 호출될 때마다 날짜를 비교해 바뀌었으면 `close()` 후 `initLog()` 로 **재오픈**한다(`serverlog.c:106`). 즉 ①은 **관측야가 바뀔 때마다 되풀이**되고, 거기서 권한이 나쁘게 잡히면 ②가 겹쳐 **그날 밤 로그가 통째로 사라진다.** 레거시가 오래 무사했던 것은 운이다.

> 교정은 `open(..., 0644)` 과 `==` → `=` 두 줄뿐이고 둘 다 명백한 오타 수정이다. 신규 `ics` 는 이 코드를 쓰지 않으므로 영향 범위는 **우리가 시험용으로 띄우는 XIS 뿐**이다.
>
> **48GB 로그 아카이브에 빈 날·누락된 날이 있는지 확인해 볼 만하다** — 있다면 이 결함의 실제 발현 기록일 수 있다. (`ics_sim/tools/scan_legacy_logs.py` 가 있는 머신에서)

## 5. 운영 설정 — 3개 사이트

세 사이트 모두 `ServerID XIS` · `ServerPort 6660` · `TTYPort /dev/ttyS0 115200` · `Verbose` 로 같고, 아래만 다르다.

| | CTIO | SAAO | SSO |
|---|---|---|---|
| 서브넷 | `192.168.14.x` | `192.168.13.x` | `192.168.15.x` |
| `Instrument` | `KMTC` | `KMTS` | `KMTA` |
| preset `UDPPort` 줄 수 | **13** | **14** | **13** |
| ├ IC relay (`:6600`) | `.102`–`.108` (7) | `.102`–`.108`, `.110` (8) | `.102`–`.108` (7) |
| ├ Caliban (`:10601`) | `.102`–`.106` (5) | `.102`–`.107` (6) | `.102`–`.107` (6) |
| └ PC-TCS (`:6606`) | `.108` (1) | 없음 | 없음 |

- **허브 자신은 `.109`** — `isisPerl/isisCmd` 가 `192.168.14.109:6660` / `192.168.15.109:6660` 을 XIS 주소로 잡고, CTIO `Config/isisrelay.ini` 의 `ISISHost` 도 `192.168.14.109` 다.
- 시리얼 속도가 두 개다. **ICS↔XIS 는 115200**(`isis.ini`), **relay↔VDOS 는 9600**(`isisrelay.ini`).
- 데몬 모드(`isisd`)는 **미사용**이다. 운영 `Config/` 에 `isisd.ini` 가 없고, 기동 스크립트가 `xterm` 안에서 대화형으로 띄운다.
- `startisis`·`stopisis`·`chkisis` 는 MODS 시절 범용 래퍼라 `/home/dts/ISIS/bin/isis` 를 본다. **KMTNet 실제 기동 경로는 `KMTN_Startup_ICS`** 이고 `…/ISIS/server/isis` 를 직접 띄운다. 둘이 어긋나 있다.

### 5.1 `isis.ini` 를 쓸 때 조심할 것 (2026-08-11 실물 기동에서 확인)

**① 한 줄이 80 바이트를 넘으면 안 된다.** `loadconfig.c:24` 의 `CFG_BUFSIZE` 가 `80` 이고 `fgets(inStr, CFG_BUFSIZE, iniFP)` 로 읽는다. 넘으면 줄이 잘리고 **잘린 뒷도막이 다음 줄로 다시 읽혀 설정 항목으로 파싱된다.**

```
Ignoring unrecognized config file entry - 이 필요하다
```

첫 기동 때 실제로 이게 떴다 — 우리가 생성한 ini 의 한글 주석(글자당 3바이트)이 80을 넘겼기 때문이다.

**그리고 위험한 쪽을 실측으로 확인했다 (2026-08-11).** 80바이트 지점 뒤가 `UDPPort 192.0.2.1 9999` 가 되도록 주석 한 줄을 심고 띄워 봤더니:

```
Ignoring unrecognized config file entry - 이 필요하다     ← 한글 꼬리: 경고
...
  Preset UDP Ports: 2 configured of 32 max:
    udp0: 127.0.0.1:6600
    udp1: 192.0.2.1:9999                                  ← 심은 꼬리: 조용히 등록
```

**같은 메커니즘인데 꼬리가 파싱 불가면 경고가 뜨고, 우연히 파싱되면 아무 말 없이 적용된다.** 운영 설정에 긴 주석 한 줄이 잘못 들어가면 아무도 모르게 엉뚱한 주소로 PING 을 뿌리게 된다는 뜻이다. `build-local.sh` 는 주석을 ASCII 로 쓰고, 생성 후 80 바이트 이상인 줄이 있으면 경고한다(긴 `--prefix` 도 여기 걸린다).

**② `Instrument` 는 파싱 버그로 값이 뒤바뀐다 — 레거시 소스의 실제 결함.** `loadconfig.c:228` 이 인자 원본으로 `valStr` 이 아니라 `argStr` 을 넘긴다:

```c
getArg(argStr, 1, argStr);     // INSTRUMENT -- 원본과 대상이 같다
getArg(valStr, 1, argStr);     // 다른 모든 항목은 이렇게 (SERVERLOG 등)
```

`argStr` 에는 **직전에 파싱된 항목의 값**이 남아 있으므로, `instID` 에 그게 그대로 복사된다. 실측에서 `Instrument KMTTEST` 를 줬는데 콘솔 `INFO` 가 이렇게 나왔다:

```
Instrument Config: /home/rtkmtnet/AICS/Logs/isis      ← ServerLog 값이다
```

**두 번째 실측에서 메커니즘이 더 분명해졌다** — preset 을 하나 넣고 다시 띄우니 이번엔 `Instrument Config: 6600` 이 나왔다. 직전 `UDPPort 127.0.0.1 6600` 이 `argStr` 에 남긴 포트 번호다. 서로 다른 값으로 두 번 재현된 셈이다.

운영 CTIO `isis.ini` 주석이 `Instrument` 를 *"optional and unused for anything in detail"* 이라 적어 둔 덕에 **아무도 눈치채지 못한 채 살아남은 버그**다. 실제로 읽는 곳이 없어 영향은 없다.

**③ 로그 파일 날짜는 UTC 가 아니라 관측야(observing night) 다 — 정상 동작.** `LogDate` 기본값이 `OBSDAY`(정오~정오 현지시각)라, `2026-08-11 01:58 UTC` 에 띄웠는데 로그는 `isis.20260810.log` 로 열렸다. SSO 현지로 8/11 오전 11:58 = 현지 정오 전이므로 **8/10 밤에 속한다.** 하룻밤이 한 파일에 담기는 관측 관례이고, 레거시 로그 이름(`ISIS.ICSci.SSO.20240725`)도 같은 규칙이다. 달력 날짜를 원하면 `LogDate UTC`.

## 6. 신규 `ics` 설계에 걸리는 것 — DevNote 정정과 확정

등록 방식은 **`EXEC_ISIS/server/` 를 운영 소스로 보고** 확정했었다([부록 A](#부록-a-xis-노드-등록--논의-전-과정) (12)). 트리 판정이 바뀌었으므로 각 결론이 여전히 유효한지 다시 확인했다. **아래가 그 재확인 결과이고, 결론만 필요하면 [`../DevNote.md`](../DevNote.md) 3.1.1 에 정리돼 있다.**

### 6.1 유효한 결론 — 근거 트리만 바뀐다

`clients.c` · `messages.c` · `commands.c` · `serverlog.c` · `utils.c` 는 두 분기가 **`#include` 헤더 이름 한 줄을 빼면 바이트 동일**하다. 따라서 아래는 그대로 성립한다.

| 부록 A (12) | 결론 | 상태 |
|---|---|---|
| ① 정적 목록 vs 동적 등록 | 클라이언트 테이블은 완전 동적, preset 은 재시작 PING 대상일 뿐 | 유효 |
| ② 테이블 키 | **노드 ID 로만** 키잉 (`strcmp(testStr, clientTab[i].ID)`), 주소는 갱신만 | 유효 |
| ③ 같은 주소에 여러 ID | 주소 충돌 검사 로직 자체가 없다 → **1안(단일 소켓 + 9개 ID) 안전** | 유효 |
| ⑤ 테이블 최대 | `MAXCLIENTS 64` | 유효 |
| ⑥ `AL` 브로드캐스트 중복 | 슬롯 전수 순회 → 9개 ID 면 **9번 받는다** | 유효 |

`interfaces.c` 의 `handShake()`(재시작 시 `XIS>AL PING` 을 시리얼 + preset UDP 에 개별 `sendto`)도 v2.9.1 에 동일하게 있다 → ④ 유효.

### 6.2 ⑧ `MAXPRESET` 미해결 항목 — **해결됐다**

부록 A ⑧ 은 *"헤더는 `MAXPRESET 8` 인데 CTIO `isis.ini` 에는 `UDPPort` 가 13줄이다. 배포 바이너리가 다른 값으로 빌드됐을 가능성"* 을 미해결로 남겼다.

**운영본이 v2.9.1 이므로 `MAXPRESET` 은 32 다.** `8` 은 은퇴한 v2.7.3 헤더의 값이었다. `isis.ini` 주석의 *"max 32"* 도 v2.9.1 헤더와 정확히 맞는다.

| | CTIO | SAAO | SSO |
|---|---|---|---|
| 사용 중 | 13 | 14 | 13 |
| 상한 | 32 | 32 | 32 |
| **여유** | **19** | **18** | **19** |

→ **신규 `ics` 를 preset 목록에 한 줄 추가하는 데 아무 제약이 없다.** 부록 A ⑨ 의 "운영 측 작업" 이 `MAXPRESET` 확인 없이 바로 진행 가능해졌다. (2안이었다면 9줄이 필요했겠지만 그 역시 여유 안이다.)

### 6.3 새로 확인된 것

- **`EXEC_ISIS` 전용 패치는 운영본에 없다.** CTIO `EXEC_ISIS/server/interfaces.c` 에는 *"srcID 가 serverID 와 같으면 메시지를 버린다"* 는 2014-09-30 자 방어 코드가 있는데, **v2.9.1 에는 없다.** 신규 `ics` 가 실수로 `XIS` 를 발신 ID 로 쓰면 운영 허브는 걸러 주지 않는다.
- **SSO 의 브로드캐스트 패치도 운영본에 없다.** SSO `EXEC_ISIS/server/messages.c` 는 `if (i != sendHost)` 를 `if (clientTab[i].port != clientTab[sendHost].port)` 로 바꿔 **송신자와 같은 포트를 쓰는 클라이언트 전부**를 브로드캐스트에서 제외한다. 이 패치는 은퇴 분기에만 있다.
  - 운영본은 `i != sendHost` 이므로, 신규 `ics` 가 `AL` 로 브로드캐스트를 쏘면 **자기가 등록한 나머지 8개 ID 앞으로 같은 데이터그램이 되돌아온다.** 자기 발신 에코를 걸러야 한다.
  - 부록 A ③ 이 근거로 인용한 *"clients that share the same port as the sending host"* 는 **주석 문구**다(원본 주석은 3개 분기 전부에 있다). 그 문구대로 동작하는 코드는 SSO 은퇴 분기뿐이다. **다만 ③ 의 결론은 ②(주소 충돌 검사 없음)만으로 성립하므로 바뀌지 않는다.**
- **운영 서버 소스는 3사이트 바이트 동일**하다(CTIO = SAAO, SSO 는 `relay/` 두 파일만 다름). 사이트별 분기를 걱정할 필요가 없다. 사이트 차이는 전부 `isis.ini` 에 있다.
- `commands.c` 콘솔 명령에 **`UDPPING <ip> <port>`** 가 있다. 신규 `ics` 를 preset 에 넣기 전에도 **XIS 콘솔에서 직접 PING 을 쏴 등록을 시험할 수 있다.**

## 7. 실물에서 확인할 것

XIS 콘솔(기동된 xterm)에서 아래 셋이면 3절 판정과 6.2절 여유가 한 번에 확정된다.

| 입력 | 확인 내용 | 기대값 |
|---|---|---|
| `VERSION` | 어느 트리가 도는지 | `2.9.1` (v2.7.3 이면 3절 판정이 틀린 것) |
| `INFO` | preset 여유 · 클라이언트 수 | `Preset UDP Ports: 13 configured of 32 max` |
| `HOSTS` | 등록된 노드 테이블 | 13개 안팎 |

기동 배너도 지표다 — v2.9.1 은 `ISIS / OSU Interactive Science Instrument Server`, v2.7.3 은 `XISIS / OSU Executive Interactive Science Instrument Server` 를 찍는다.

이어서 신규 `ics` 연동:

> ### ⚠️ 경고 — 레거시 ICS/IC 가 살아 있는 운영 XIS 에 `ics_sim` 을 등록하지 말 것
>
> XIS 의 `updateHosts()`(`src/server/clients.c:83`)는 이미 아는 노드 ID 로 메시지가 오면 **그 데이터그램의 (IP,port) 로 테이블을 무조건 덮어쓴다** — 107행에서 ID 만 `strcmp` 로 비교하고, 108~112행에서 `addr`·`port` 를 검사 없이 갱신한다. **주소 충돌 검사는 없다**(3절 · 6.1절 ②③에서 확정한 사실).
>
> 따라서 레거시 `ICS`·`K.IC` 등이 등록된 상태에서 `ics_sim` 이 9개 ID 로 PING 하면 **그 순간 9개 ID 의 라우팅을 전부 가로챈다.** 이어서 레거시 쪽이 아무 메시지나 보내면 라우팅은 도로 빼앗기고, 양쪽이 트래픽을 내는 동안 **각 ID 의 라우팅이 두 주소 사이를 오가는 플래핑**이 된다 — 관측 명령이 어느 쪽에 도착할지 메시지 단위로 갈린다.
>
> **아래 절차는 반드시 레거시 ICS/IC(및 relay)를 정지한 뒤에, 또는 운영과 분리된 시험용 XIS 인스턴스에서 수행할 것.**

1. `ics_sim` 을 `bind_host = 0.0.0.0` 으로 띄우고 `--xis-host` 로 XIS 를 가리킨다.
2. XIS 콘솔에서 `UDPPING <sim_ip> <sim_port>` → 시뮬이 9개 ID 로 PONG 하는지 본다. 이어 `HOSTS` 로 9개가 전부 테이블에 올랐는지 확인.
3. `tools/isisPerl/<site>/isisCmd` 로 `OBS>K.IC STATUS` 류를 주입해 라우팅을 확인한다. 실패하면 `ERROR: No Route to Destination Host K.IC - host is unknown/unlisted` 가 돌아온다 — 이게 판정 기준이다.
4. 통과하면 운영 `isis.ini` 에 `UDPPort <sim_ip> <sim_port>` **한 줄**을 추가하고 XIS 를 재시작해, `XIS>AL PING` 에 9개 PONG 이 나가는지 본다.

## 8. 계획 / 남은 일

- [x] **7절 실물 확인** — **완료 (2026-08-11).** `VERSION` = `2.9.1`(3절 트리 판정과 일치), `INFO` = `Preset UDP Ports: n configured of 32 max`(6.2절 상한 확정). 부수로 5.1절의 세 가지가 실측으로 드러났다.
- [ ] **▶ 다음에 여기서 시작 — `ics_sim` 연동 (9개 ID 등록 실증)**

  준비는 끝나 있다. SSO AIC 실험실 머신에 XIS 가 빌드·설치돼 있고 설정도 깨끗하다(`~/AICS/bin/isis` · `~/AICS/Config/isis.ini`, preset `127.0.0.1:6600` 하나). 레거시 ICS/CB 는 이 머신에 없어 7절 경고에 걸리지 않는다.

  ```bash
  ~/AICS/bin/isis -f$HOME/AICS/Config/isis.ini              # 창 1
  cd ~/CEU/.../ics_sim && python3 -m ics_sim --xis-host 127.0.0.1 --xis-port 6660   # 창 2
  ```

  XIS 콘솔에서 `HOSTS` — **`ICS` + `{K,M,T,N}.IC` + `{K,M,T,N}.CB` 9개가 다 올라오면 성공.** 안 되면 `UDPPING 127.0.0.1 6600` 으로 찔러 본다. 실패 신호는 `ERROR: No Route to Destination Host K.IC - host is unknown/unlisted`(부록 A (10)).

  **이것이 남은 마지막 미실증 항목이다** — 소스로는 안전하다고 판정했지만(`clients.c` 가 ID 로만 키잉하고 주소 충돌 검사가 없음, 6.1절 ②③) 48GB 로그 전체에 같은 (IP,port) 에 여러 ID 를 올린 사례가 한 건도 없어 실물 확인이 남아 있었다. `transport.feed()` 테스트로는 라우팅 단계를 건너뛰어 절대 드러나지 않는 경로다.

  이어서 `tools/isisPerl/sso/isisCmd` 로 `OBS>K.IC STATUS` 류를 주입하면 라우팅까지 확인된다.
- [x] **DevNote 3.1.1 갱신** — **완료 (2026-08-06 개편 때).** DevNote 3.1.1 은 근거 트리를 `ISIS/server/`(v2.9.1) 로 정정한 결론·규약본으로 재작성됐고, ⑧(`MAXPRESET`) 해결도 반영됐다. 당시 갱신 대상이던 '(12)' 는 이 문서 부록 A 로 이관돼 이미 정정 주석을 달고 있다.
- [x] **`ics_sim` 자기 발신 에코 처리** — **구현 완료 (2026-08-08, DevNote 3.1.2).** 점검에서 브로드캐스트 에코보다 심각한 **유니캐스트 루프백**(시퀀서가 자기 노드 앞으로 쏜 ERASE/SHOPEN 이 되돌아와 재실행)이 드러나, `cmd_ping()` 수준이 아니라 **수신 초입의 자기 발신 필터**로 구현했다. 브로드캐스트 중복 억제(`broadcast_dedup_sec`) 포함, `test_xis_echo.py` 15개가 검증.
- [x] **재빌드 검증** — **완료 (2026-08-11).** SSO AIC 리눅스 머신에서 `build-local.sh` 로 `isis`·`isisd` 빌드 성공. 걸림돌은 넷이었고(4.2절) 그중 ④ 는 실제 컴파일에서만 드러나 스크립트에 반영했다. 남은 것은 경고 하나뿐 — `isisd.c:308` 의 `sprintf` 가 256바이트 버퍼에 최대 286바이트를 쓸 수 있다는 `-Wformat-overflow`. **KMTNet 은 `isisd`(데몬판)를 쓰지 않으므로**(운영 `Config/` 에 `isisd.ini` 가 없고 xterm 대화형으로 띄운다) 실무 영향은 없다.
- [ ] (선택) 운영 머신에서 `isis` 실행 바이너리를 회수해 `install/bin/` 에 추가.

## 9. 참고

| 문서 | 내용 |
|---|---|
| [`../DevNote.md`](../DevNote.md) 3.1.1 | **결론과 규약** — 지금 지켜야 할 것. 논의 전 과정은 이 문서 부록 A 로 이관됐다 |
| [`../SMC_CLAUDE.md`](../SMC_CLAUDE.md) | 신규 `ics` 작업 컨텍스트. "XIS 노드 등록 — 해결됨" 절 |
| [`../../ics_legacy/ics_legacy_report.md`](../../ics_legacy/ics_legacy_report.md) | 레거시 전체. 1.2절 ISIS/XIS · 1.3.1절 VDOS+relay 3계층 구조 |
| `src/doc/ICIMACS2.txt` | IMPv2 프로토콜 원본 정의 |
| `src/doc/ISIS_commands.txt` | ISIS 콘솔·메시지 명령 세트 |
| `src/00README.txt` | ISIS 패키지 설계 의도 (R. Pogge) |
| `branches/xisis-2.7.3/00README.txt` | XISIS 분기의 목적 (J. Mason, 2014-02-14) |

## 10. 이력

| 날짜 | 내용 |
|---|---|
| 2026-08-11 | **`build-local.sh` 추가.** 보관본을 건드리지 않고 작업 사본에서 빌드·설치하는 스크립트. 정적 분석으로 현대 툴체인 걸림돌 3가지(CRLF · `logMessage` 리터럴/`register` · `.c.o` 서픽스 규칙)를 찾아 처리했고 4.2절에 정리. 4절이 안내하던 "보관본 안에서 `./build`" 는 체크섬을 깨뜨리므로 폐기 |
| 2026-08-11 | **첫 실물 빌드·기동 성공** (SSO AIC 리눅스, Ubuntu 24.04 / g++ 13.3.0). `MAXPRESET 32` 실물 확정, 설정 파일 함정 3종 발견(5.1절), `serverlog.c` 런타임 결함 2종 교정(4.3절). 다음은 `ics_sim` 연동 |
| 2026-08-11 | **첫 실물 빌드 성공** (SSO AIC 리눅스). `build-local.sh` 추가 + 실측으로 걸림돌 ④(포인터/정수0 순서비교) 발견·반영. 4절을 재작성하고, 보관본 안에서 `./build` 하라던 이전 안내는 폐기(체크섬 파괴) |
| 2026-08-08 | **정정 일괄 반영.** 7절에 운영 XIS 동시 등록 금지 경고 추가(`updateHosts` 의 무조건 덮어쓰기 → 라우팅 가로채기·플래핑), 8절 ② DevNote 3.1.1 갱신 완료 처리, 보관 파일 수 162 로 통일(2절·이력의 163 은 오기), 부록 A 교차참조 정정((10)의 5.6.3절 → `ics_legacy_report.md` 명시, ⑥의 '3.1.1 (1)' → 부록 (1)), (10)→(12) 지점에 (11) 위치 안내 추가. MANIFEST 신규 파일 목록에 `.gitattributes` 보충 |
| 2026-08-06 | **DevNote 3.1.1(449줄)을 부록 A 로 이관.** DevNote 는 결론·규약만 남겨 1,889→1,482줄. XIS 허브 논의가 "OBSAgent 인터페이스 규약" 장 안에 있던 자리 문제도 함께 해소 |
| 2026-08-05 | 폴더 신설. `__dts_legacy` 3사이트 백업에서 XIS 관련 자산 162 파일 수집·정리. **운영본이 XISIS v2.7.3 이 아니라 stock ISIS v2.9.1 임을 확인**(3절), 그 결과 DevNote ⑧ `MAXPRESET` 미해결 항목 해결(6.2절) |

---

## 부록 A. XIS 노드 등록 — 논의 전 과정

> **DevNote 3.1.1 에서 이관 (2026-08-06).** 신규 `ics` 가 XIS 에 9개 노드 ID 로 등록하는 방식을 정하기까지의 조사·논쟁 기록 전부다. **지금 지켜야 할 규약과 확정 사실은 [`../DevNote.md`](../DevNote.md) 3.1.1 에 요약돼 있다** — 여기는 "왜 그렇게 정했나"를 되짚을 때 여는 문서다.
>
> 중간에 근거 없이 단언한 지점이 있었고 사용자가 그걸 짚어 바로잡았다. 같은 착각을 반복하지 않으려면 과정이 필요해서 남긴다. **(1)~(11)은 확정 전의 기록이다** — 현재 상태는 (12)(14) 와 이 문서 3·6절에 있다.

### (1) 문제 발견 — 수신 9노드를 절반만 구현했다

DevNote 3.1 에서 "수신은 9개 노드 ID 전부"라고 정해 놓고, 코드는 절반만 하고 있었다. `NodeRouter` 는 9개 ID를 내부 라우팅했지만 기동 시 발신하는 건 **`ICS>AL PING` 한 줄뿐**이었다.

IMPv2에는 등록 API가 없다. 노드가 **자기 이름으로** 아무 메시지나 보내면 XIS가 "노드ID → 그 데이터그램의 (IP,port)"를 기억하는 것이 전부다(`ics_legacy_report.md` 1.2절). 따라서 `ICS` 이름으로만 보내면 XIS는 `ICS` 하나만 안다. 결과:

- `OBS>K.IC STATUS`(kstatus), `OBS>K.IC DMAWAIT`, `OBS>*.IC DATASOURCE` → XIS가 `K.IC` 를 모르니 **라우팅 실패**
- `emit_node_mode=legacy` 면 첫 노출 때 `K.IC>ICS DONE: …` 가 나가면서 그제야 등록 → **기동 직후~첫 노출 전에는 안 됨**
- `emit_node_mode=merged` 면 모든 발신이 `ICS` 이름이라 **영영 등록 안 됨**

**테스트가 이걸 못 잡은 이유**: 테스트는 `transport.feed()` 로 메시지를 직접 주입해 **XIS 라우팅 단계를 통째로 건너뛴다.** direct-reply 모드(기본)에서도 상대가 우리 주소로 직접 쏘므로 드러나지 않는다. **XIS 경유 모드로 바꾸는 순간에만 드러나는 종류의 결함**이다.

### (2) 근거 없는 단언과 그 정정

처음에 나는 해법으로 *"9개 ID 각각 PING을 보내면 된다. XIS는 노드ID→주소 매핑이라 9개가 같은 주소를 가리켜도 문제없다"* 고 했다. **근거가 부족한 단언이었다.**

사용자가 곧바로 물었다 — *"XIS가 동일 IP와 포트로 들어온 ping에 잘 대응할 수 있을까? 동일 IP/port의 노드는 ID가 덮어씌워지는 것은 아닐까?"* 매핑이 반대 방향((IP,port) → 노드ID)이면 나중 등록이 앞 등록을 덮어쓴다. 타당한 지적이다.

### (3) 로그 실측 — 방향은 확인됐다

CTIO 하루치 로그에서 노드별 주소 사용을 집계했다:

| 노드 | 대표 주소 | 사용한 주소 개수 |
|---|---|---:|
| `K.IC` | 192.168.14.102:6600 | 1 |
| `K.CB` | 192.168.14.102:**10601** | 1 |
| `ICG` | 192.168.14.108:6600 | 1 |
| `TC` | 192.168.14.108:**6606** | 1 |
| `OBS` | 192.168.14.109:6650 | 1 |
| `ICS` | `/dev/ttyS0` | 1 |
| **`ABC`** | 192.168.14.108:39026 … | **4,077** |
| **`GMON`** | 192.168.14.108:42731 … | **8,134** |

**새로 확인된 사실 두 가지:**

**(a) `ABC`/`GMON` 은 포트를 고정하지 않는다.** 매 메시지를 ephemeral 포트로 보낸다 — 하루에 주소가 각각 4,077개, 8,134개다. 그런데도 `TC>'ABC DONE: goto focus and tip-tilt commanded`, `OBS>GMON DONE: CamStatus=…` 응답을 정상적으로 받는다.

→ **"지금 GMON이 어디 있지?"를 물을 수 있어야 가능한 일**이므로, XIS는 반드시 **노드ID → 주소** 방향 테이블을 갖고 매 수신마다 갱신한다. 이 방향은 확실하다. 주소→노드ID 만으로는 `dest=GMON` 을 어디로 보낼지 알 수 없다.

**(b) 그러나 동시에 같은 (IP,포트)를 쓴 노드는 48GB 어디에도 없다.** 같은 호스트에 있는 노드들도 전부 포트를 달리 쓴다 — `K.IC`:6600/`K.CB`:10601, `ICG`:6600/`TC`:6606. `ABC`/`GMON` 이 같은 포트 번호로 잡히는 사례가 다수 있지만 그건 **시간차 재사용**이지 동시 점유가 아니다.

> 레거시에서 `K.IC`~`N.IC` 가 전부 6600을 쓸 수 있었던 것은 **각자 다른 호스트**에 있었기 때문이다(.102/.103/.104/.105). 시뮬은 한 호스트라 같은 방식을 쓸 수 없다.

### (4) XIS 등록 로그 — 테이블은 노드 ID로 키잉된다 (2026-08-04 추가 확인)

XIS는 클라이언트를 등록할 때 로그를 남긴다. 이걸 놓치고 있었다:

```
2025-04-02T23:30:56.783833 [192.168.14.102:10601] K.CB>XIS PONG
2025-04-02T23:30:56.783850 Added UDP Client K.CB on host 192.168.14.102:10601
```

CTIO 60일치에서 `Added UDP Client` 99건을 분석한 결과:

| 노드 | 등록 횟수 | 등록에 쓰인 주소 개수 |
|---|---:|---:|
| `K.IC`·`M.IC`·`T.IC`·`N.IC`·`*.CB`·`ICG`·`G.IC`·`TC`·`OBS` (고정 포트) | 각 6 | 각 **1** |
| `ABC`·`GMON` (ephemeral 포트) | 각 7 | 각 **7** |

**결정적 관찰**: `ABC`/`GMON` 은 하루에 수천 개 주소를 쓰는데 `Added` 는 **7번뿐**이고, 그 횟수가 XIS 재시작 횟수와 같다.

→ **XIS는 이미 아는 ID면 주소만 조용히 갱신하고, 처음 보는 ID일 때만 `Added` 를 남긴다.** 테이블이 **주소**로 키잉돼 있었다면 `ABC`/`GMON` 이 포트를 바꿀 때마다(하루 수천 번) `Added` 가 떴어야 한다. 그러지 않는다는 것은 **테이블이 노드 ID로 키잉된다**는 강력한 증거다.

또한 `Added UDP Client` 99건 중 **같은 (IP,port)에 서로 다른 ID가 등록된 사례는 0건**이다 — (3)절 관찰의 재확인.

**부수 관찰**
- **`ICS` 는 `Added UDP Client` 목록에 없다.** 시리얼이라 UDP 클라이언트가 아니기 때문이다. 우리 시뮬은 `ICS` 를 **UDP로** 등록하는데, 실제 XIS가 한 번도 겪어본 적 없는 구성이다.
- 등록 직후 `XIS>GMON ERROR: No Route to Destination Host OBS` 가 뜬다 — 재시작 후 `OBS` 가 아직 재등록 전이라 GMON 폴링이 실패한 것이다. `OBS` 는 XIS에 PING을 하루 2회밖에 안 보내므로 **실제 운영에 이 공백이 존재한다.**
- `Added` 를 유발한 직전 메시지는 PONG이 대부분이지만 `gmon>obs sysstatus`, `abc>tc fttgoto` 같은 **평범한 명령도 등록을 유발**한다. 등록에 특별한 메시지가 필요하지 않다는 뜻이다.

### (5) 남은 불확실성

(4)로 위험도는 상당히 낮아졌지만 **완전한 증명은 아니다.**

- "테이블이 ID로 키잉된다"와 "같은 주소를 여러 ID가 공유해도 된다"는 **별개 명제**다. 등록 시 같은 주소의 기존 항목을 정리하는 로직이 따로 있을 가능성을 배제할 수 없다.
- **XIS 서버 소스가 저장소에 없다.** 있는 건 클라이언트 라이브러리(`ISISclient`)뿐이다.
- **실제 배치에서 한 번도 시험된 적 없는 구성**이라는 사실은 그대로다.

> 에러 문구의 `host is unknown/**unlisted**` 를 보고 "XIS에 정적 호스트 목록이 있을지 모른다"고 우려했으나, (4)의 `Added UDP Client` 로그가 **동적 등록**임을 보여준다. "unlisted" 는 그 동적 목록에 없다는 뜻으로 읽는 것이 자연스럽다. 정적 설정 파일 우려는 낮춰도 될 것 같다 — 다만 소스로 최종 확인한다.

### (6) 1안 / 2안

| | **1안 — 단일 소켓** | **2안 — 노드별 소켓** |
|---|---|---|
| UDP 소켓 | 1개 (`bind_port`) | 9개 (노드마다 포트 하나) |
| 등록 | 9개 ID로 PING을 **같은 포트에서** 발신 | 각 노드가 **자기 포트에서** 자기 이름으로 PING |
| XIS 호환성 | **미검증** — 같은 (IP,port)에 9개 ID | **보장** — 레거시 배치와 동일 구조 |
| 구현 비용 | 낮음 (현재 구조 그대로) | 중간 (`UdpEndpoint` 9개, 발신 시 소켓 선택) |
| 설정 부담 | 포트 1개 | 포트 9개 배정 필요 |

2안의 포트 배정안(레거시 관례를 한 호스트에 맞춰 편 것):

```
ICS   6600
K.IC  6601   M.IC  6602   T.IC  6603   N.IC  6604
K.CB 10601   M.CB 10602   T.CB 10603   N.CB 10604
```

### (7) 결정 — 일단 1안, XIS 소스 확보 후 재검토

**사용자 결정 (2026-08-04)**: ISIS/XIS 소스를 찾아 공유하기로 했고, 그때까지는 **1안으로 완성해 커밋**한다.

구현:
- `Emitter.register_ping(node_id)` — src를 그대로 지정한다. **`emit_node_mode` 를 따르지 않는다** — merged는 *발신 이름*만 통일하는 옵션이고 수신은 언제나 9개여야 하기 때문이다.
- `IcsSim.register()` — `router.registered_ids` 9개 전부로 PING.
- `[transport] register_all_nodes` (기본 `true`) — 끄면 `ICS` 만 등록하고 경고를 낸다. XIS가 다중 등록을 거부하는 것으로 밝혀졌을 때의 임시 탈출구이지만, **그 상태로는 개별 IC 명령을 받을 수 없다.**

검증: `test_startup_registers_all_nine_nodes` · `test_registration_ignores_emit_node_mode`(legacy/merged 양쪽) · `test_register_all_nodes_false_only_registers_ics`.

### (8) 2안으로 전환해야 하는 조건

아래 중 하나라도 확인되면 2안으로 간다.

1. **XIS 소스 확인 결과** 클라이언트 테이블이 주소로 인덱싱되거나, 등록 시 같은 주소의 기존 항목을 제거한다.
2. **실물 시험에서** 9개 PING 후 `OBS>K.IC STATUS` 가 도달하지 않는다. 가장 빠른 확인법 — XIS를 띄우고 시뮬을 `--xis-host` 로 붙인 뒤 `kstatus` 를 쳐 본다.
3. XIS 로그에 등록 교체/거부를 시사하는 메시지가 남는다.

**XIS 소스를 받으면 확인할 것** (우선순위 순)

1. **노드 목록이 정적 설정인가 동적 등록인가** — 에러 문구의 `host is unknown/**unlisted**` 가 목록의 존재를 시사한다(아래 (9)절). 설정 파일 기반이라면 시뮬을 **그 목록에 추가**해야 하고 PING만으로는 부족하다. **1안/2안보다 근본적인 문제이므로 이것부터 본다.**
2. **클라이언트 테이블의 인덱스 키** — 노드ID인지, (IP,port)인지, 둘 다인지
3. **같은 주소로 다른 ID가 등록될 때의 처리** — 추가인가, 교체인가, 거부인가
4. **재시작 시 등록 요청의 정확한 형태** — (9)절에서 "PING을 뿌린 뒤 로그를 연다"는 순서까지는 확인됐다. 남은 것은 그것이 `AL` 브로드캐스트 한 방인지 알려진 노드들에 개별 PING인지, 그리고 재시작 직후 XIS의 테이블이 비어 있을 텐데 **누구에게** 보내는지다(= 어딘가에 노드 목록이 있다는 뜻일 수 있다)
5. **테이블 최대 크기** — 9개를 더 얹을 여유가 있는지
6. **`AL`/`ALL` 브로드캐스트가 같은 주소의 여러 ID에게 어떻게 나가는지** — 우리 소켓이 하나뿐이라 같은 메시지를 9번 받을 수 있다

마지막 항목은 1안 고유의 부작용이라 실물 시험 때 반드시 같이 볼 것. 지금 코드는 브로드캐스트를 `ICS` 가 대표로 처리하므로(`NodeRouter.resolve`) 중복 수신이 와도 9번 응답하지는 않지만, 수신 트래픽은 9배가 된다.

### (9) XIS 재시작 시의 재등록 — 실측 (2026-08-04)

*"XIS가 재실행될 때 아마도 `>AL ping` 할 것 같은데"* 라는 가설을 로그로 확인했다. **맞다.**

샘플 로그에서 **하루 중간에 XIS가 재시작한 사례 16건**을 찾았고, 16건 전부 같은 패턴이다:

```
XIS runtime log (re)started at UTC 2024-09-02T06:18:00.059046
  TC>XIS PONG     M.CB>XIS PONG   G.CB>XIS PONG   K.CB>XIS PONG
  N.CB>XIS PONG   T.CB>XIS PONG   ICG>XIS PONG    N.IC>XIS PONG
  K.IC>XIS PONG   T.IC>XIS PONG   M.IC>XIS PONG   G.IC>XIS PONG
```

**재시작 직후 12개 노드가 전부 `>XIS PONG` 을 보낸다.** PONG은 PING에 대한 응답이므로 XIS가 재시작하면서 등록 요청을 뿌렸다는 뜻이다.

**PING은 로그를 열기 전에 나간다 (확인됨).** 로그에 `XIS>AL PING` 이 찍혀 있지 않다 — 샘플 전체에서 **XIS 발신 PING이 로그에 남은 횟수 0**이다. XIS의 다른 발신은 잘 남는데(`XIS>K.IC PONG` 28,457건) 그 PING만 없다.

로그 재시작을 **첫 로그 항목** 기준으로 분류하면 성격이 갈린다:

| 첫 로그 항목 | 건수 | 정체 |
|---|---:|---|
| `K.CB>K.IC REQ INITDISK` | 48 | 시스템 전체 콜드 스타트 — 디스크 초기화가 먼저 |
| `TC>AL ping` | 33 | 시스템 전체 기동 — TC의 브로드캐스트가 첫 트래픽 |
| `OBS>TC TSTAT` 등 (PONG 0건) | 17 | **정오 정각 로그 로테이션** — XIS는 계속 실행 중 |
| **`*.CB>XIS PONG` · `TC>XIS PONG`** | **약 12** | **XIS 단독 재시작** |

마지막 부류가 결정적이다. XIS 단독 재시작에서는 **로그의 맨 첫 줄이 노드의 PONG**이고, 재시작 타임스탬프로부터 **1~1.5 ms** 후다:

```
XIS runtime log (re)started at UTC 2025-04-02T23:30:56.782917
2025-04-02T23:30:56.783833  K.CB>XIS PONG      ← 0.9 ms 후, 로그의 첫 항목
2025-04-02T23:30:56.783850  Added UDP Client K.CB on host 192.168.14.102:10601
```

PING이 로그에 없는데 PONG이 1 ms 안에 도착하는 것으로 보아 PING이 확실히 나갔다. **왜 로그에 없는지는 (12)④에서 소스로 확인했다** — `handShake()` 가 `write()`/`sendto()` 를 직접 호출하고 `logMessage()` 를 거치지 않기 때문이다. **XIS는 자신이 보내는 handshake PING을 로깅하지 않는다.**

> **정정**: 처음에는 "로그 파일을 열기 전에 보냈을 것"으로 추론했으나 **틀렸다.** `main.c` 의 실제 순서는
> `loadConfig() → openSocket() → initLog() → 메인 루프 진입 → doStartup=COLD_START → handShake()`
> 로, **로그가 먼저 열린다.** DevNote 12.9 참고.

**여기서 따라나온 질문 — 테이블이 비었는데 누구에게 보내나?**

재시작 직후 XIS의 클라이언트 테이블은 비어 있다((4)절의 `Added UDP Client` 가 그 뒤에 찍히는 것이 근거다). 그런데도 PING이 모든 노드에 닿는다. 당시 두 가설을 세웠다 — (a) IP 서브넷 브로드캐스트, (b) 어딘가에 노드 목록이 있다.

**(b)가 맞았다.** `isis.ini` 의 preset UDP 목록(`UDPPort <ip> <port>`)에 개별 `sendto` 한다((12)④⑦). IP 브로드캐스트가 아니므로 `bind_host` 가 `127.0.0.1` 이어도 **그 자체로 PING을 놓치지는 않는다** — 다만 외부 장비와 통신하려면 어차피 `0.0.0.0` 이 필요하다.

**평시 재등록 경로도 두 가지 더 있다:**

| 경로 | 빈도 (CTIO 하루) | 성격 |
|---|---|---|
| `TC>AL ping` → 전 노드가 `>TC PONG` | 138회 (전체 샘플) | TC 기동 시. 브로드캐스트 한 번에 11개 노드가 각자 이름으로 응답 |
| `*.IC>XIS PING` → `XIS>*.IC PONG` | 노출당 1회 (K.IC 191, M/T/N.IC 각 189) | 원래 목적은 디스크 쓰기 완료 타이밍 신호(DevNote 4.1)지만, **부수 효과로 매 노출마다 등록이 갱신된다** |

즉 레거시는 **노출을 한 번만 해도 스스로 복구**됐다. 우리 시뮬은 통합 구조라 그 PING/PONG 편법이 불필요해 뺐고, 그러면서 **자동 복구 효과도 같이 잃었다.**

**우리 시뮬의 현재 동작 (실측)**

| 받은 메시지 | 시뮬 응답 |
|---|---|
| `XIS>AL PING` | `ICS>XIS PONG` — **1개뿐** |
| `TC>AL ping` | `ICS>TC PONG` — **1개뿐** |

브로드캐스트를 `ICS` 가 대표로 처리하도록 만들어서(`NodeRouter.resolve` 가 `AL` → `ICS`) **XIS 재시작 후 `ICS` 하나만 재등록되고 나머지 8개는 영영 돌아오지 않는다.** 레거시는 노드마다 프로세스가 따로라 각자 PONG을 보냈기에 문제가 없었다.

**→ 고쳐야 할 사항**
1. ~~**브로드캐스트 PING에는 9개 노드 전부로 PONG**~~ — **구현 완료 (2026-08-04)**. `cmd_ping()` 이 `msg.is_broadcast` 이면 `router.registered_ids` 전부로 PONG 한다. XIS 재시작 후 재등록의 **유일한 경로**이므로 필수였다((12)⑨).
2. **주기적 재등록** (`register_interval_sec`) — 아직 없다. preset 목록에 등록되면 (1)만으로 충분하므로 필수는 아니고, XIS가 조용히 재시작하고 아무도 브로드캐스트를 안 쏘는 경우를 위한 **안전망**이다. 레거시는 노출당 PING이 이 역할을 했다. **미착수, 우선도 중간.**

### (10) 라우팅 실패는 에러로 통보된다 — 실물 시험의 판정 기준

```
XIS>OBS  ERROR: No Route to Destination Host K.IC - host is unknown/unlisted
XIS>GMON ERROR: No Route to Destination Host OBS  - host is unknown/unlisted
XIS>ICG  ERROR: No Route to Destination Host G.IC - host is unknown/unlisted
```

등록되지 않은 노드로 메시지를 보내면 **발신자에게** 이 에러가 돌아온다. 실물 시험의 판정이 명확해진다 — 9개 PING 후 `kstatus` 를 쳤을 때 `No Route to Destination Host K.IC` 가 오면 등록 실패다.

> **"unknown/`unlisted`" 라는 단어에 주의.** "unlisted"는 XIS가 **호스트 목록을 갖고 있다**는 뉘앙스다. 순수 동적 등록이 아니라 **설정 파일에 노드 목록이 있을 가능성**이 있고, 그렇다면 시뮬을 그 목록에 **등록해 주어야** 하며 PING만으로는 부족할 수 있다. **1안/2안보다 더 근본적인 문제**이므로 소스 확인 시 최우선으로 볼 것.

> 부수 관찰: 목적지가 깨진 사례도 있다 — `No Route to Destination Host 0<0xef><0xbf><0xbd>ICG`, `Host <0xef><0xbf><0xbd>ZY´ZY<0xef><0xbf><0xbd>`. [`../../ics_legacy/ics_legacy_report.md`](../../ics_legacy/ics_legacy_report.md) 5.6.3절(현상 C — 버퍼 겹침·전송 절단)의 전송 손상이 라우팅 실패로 드러난 것이다.

> **절 순서 안내**: (11)(함께 확인된 포트 설정)은 유실된 것이 아니라 **이 문서 맨 끝, (14) 뒤에 있다.** 여기서는 (12)로 바로 이어진다.

### (12) **XIS 서버 소스 확인 — 결론** (2026-08-04)

사용자가 `ics_legacy/__dts_legacy/` 에 **ICS 컴퓨터(icsci 서버)의 `dts` 폴더 백업**을 3개 사이트분 올려 주었다. `EXEC_ISIS/server/` 에 **XIS 서버 소스 전체**가 들어 있다 — `clients.c` · `messages.c` · `interfaces.c` · `main.c` · `loadconfig.c` · `xisisserver.h`. (클라이언트 라이브러리는 `TCSAgent/__reference/ISISclient` 와 `OBSAgent/OBSAgent.latest/ISISclient` 에도 있다.)

> ### ⚠️ 근거 트리 정정 (2026-08-05) — 먼저 읽을 것
>
> **이 절이 근거로 삼은 `EXEC_ISIS/server/` 는 운영본이 아니다.** 백업에는 허브 트리가 셋 있고(`ISIS/` v2.9.1 · `EXEC_ISIS/` = XISIS v2.7.3 · `ISIS_V1/` v2.7.3), **실제로 도는 것은 stock `ISIS/` v2.9.1** 이다. 로그에 `XIS` 로 보이는 것은 `Config/isis.ini` 의 `ServerID XIS` 때문이지 XISIS 를 쓰기 때문이 아니다. 판정 근거 6가지는 이 문서 3절, 정정 경위는 12.12.
>
> **아래 ①②③④⑤⑥⑦ 은 그대로 유효하다** — `clients.c` · `messages.c` · `commands.c` · `serverlog.c` · `utils.c` 가 두 분기에서 **`#include` 헤더 이름 한 줄을 빼고 바이트 동일**하기 때문이다. 인용한 코드가 곧 운영본의 코드다.
>
> **바뀌는 것은 둘뿐이다.**
> - **⑧ `MAXPRESET` 미해결 항목이 해결됐다** — v2.9.1 은 `32` 다(v2.7.3 의 `8` 이 아니라). 아래 ⑧ 참조.
> - **③ 이 인용한 브로드캐스트 주석은 운영본 코드와 일치하지 않는다.** 결론은 안 바뀐다. 아래 ③ 참조.
>
> 그리고 `EXEC_ISIS` 에만 있는 방어 코드 하나가 **운영본에는 없다** — 아래 (14) 참조.

**(8)절의 6개 질문에 전부 답이 나왔다.**

#### ① 정적 목록인가 동적 등록인가 → **둘 다, 역할이 다르다**

- **클라이언트 테이블은 완전 동적**이다. `updateHosts()` 가 메시지를 받을 때마다 호출되어 등록/갱신한다. 정적 화이트리스트는 없다.
- **다만 재시작 시 PING을 뿌릴 대상은 `isis.ini` 의 preset 목록**(`UDPPort <ip> <port>`)이다. 이 목록에 없으면 XIS 재시작 시 PING을 받지 못한다.

→ (10)절의 `host is unknown/**unlisted**` 는 **동적 목록에 없다**는 뜻이 맞다. 정적 설정 파일 우려는 해소됐다.

#### ② 테이블 인덱스 키 → **노드 ID만. 주소는 비교에 쓰이지 않는다**

```c
// clients.c  updateHosts()
strcpy(testStr, hostID);
upperCase(testStr);                              // ID는 대문자로 정규화해 저장

if (isis.numClients > 0) {
  for (i=0; i<MAXCLIENTS; i++) {
    if (strcmp(testStr, clientTab[i].ID)==0) {   // ← ID로만 비교
      clientTab[i].method = method;
      clientTab[i].fd     = fd;
      clientTab[i].addr   = addr;                // ← 주소는 그냥 갱신
      clientTab[i].port   = port;
      clientTab[i].tstamp = timeStamp;
      return (i);
    }
  }
}
// 없으면 method==UNASSIGNED 인 첫 빈 슬롯에 새로 추가
```

(4)절에서 로그로 추론한 "ID로 키잉된다"가 소스로 확정됐다.

#### ③ 같은 주소에 여러 ID → **문제없다. 설계상 예상된 상황이다**

- 주소 충돌 검사 로직이 **아예 없다.** 각 ID가 자기 슬롯을 갖는다. ← **결론은 전적으로 이것 하나에 달려 있다.**
- `messages.c` 의 클라이언트 브로드캐스트 주석도 같은 상황을 언급한다:
  > *"it must pass along the message to all known hosts EXCEPT the sending host **and all clients that share the same port as the sending host**"*

  **여러 클라이언트가 한 포트를 공유하는 상황을 작성자가 상정하고 있었다는 뜻이다.**

→ **1안(단일 소켓 + 9개 ID PING)은 안전하다. 확정.** 2안으로 전환할 이유가 없어졌다.

> **정정 (2026-08-05).** 처음 이 절을 쓸 때 위 주석을 *"코드가 명시적으로 다룬다"* 고 적었는데, **주석이지 코드가 아니었다.** 운영본(v2.9.1)의 실제 분기는 `if (i != sendHost)` — 송신 **슬롯 하나만** 제외한다. 주석대로 포트를 비교하는 코드(`clientTab[i].port != clientTab[sendHost].port`)는 **SSO 의 은퇴 분기 `EXEC_ISIS/server/messages.c` 에만** 있고, 그 사이트가 원본을 `OLD.messages.c` 로 남겨 둔 로컬 패치다.
>
> **결론은 바뀌지 않는다** — ③ 은 위 첫 항목(충돌 검사 없음)만으로 성립한다. 다만 근거 하나가 빠졌으므로 강도를 낮춰 적어 둔다. **실무상 영향은 ⑥ 에 있다.**

#### ④ 재시작 시 등록 요청 → **`XIS>AL PING` 을 시리얼 + preset UDP 포트에 개별 전송**

```c
// interfaces.c  handShake()
//   "Sends a '>AL PING' message to all open serial ports and all preset
//    UDP ports. This is a blind broadcast that should lead to 'PONG's back
//    from any ISIS clients..."
sprintf(message,"%s>AL PING\r", isis.serverID);      // → "XIS>AL PING\r"
for (iPort=0; iPort<isis.numSerial; iPort++)  write(ttyTab[iPort].fd, message, ...);
for (iPort=0; iPort<isis.numPreset; iPort++)  sendto(..., udpTab[iPort], ...);
```

**사용자 가설이 소스로 확정됐다.** IP 서브넷 브로드캐스트가 아니라 **preset 목록에 개별 `sendto`** 다.

#### ⑤ 테이블 최대 크기 → **`MAXCLIENTS 64`**

현재 운용은 13개 안팎이다. 9개를 더 얹어도 여유가 충분하다. 초과 시 `ERR_HOSTS_FULL(-3)`.

#### ⑥ `AL` 브로드캐스트 중복 수신 → **9개 ID면 9번 받는다**

```c
// messages.c  broadcastMessage(), sendHost == ISIS_SERVER 인 경우
for (i=0; i<MAXCLIENTS; i++) {
  if (clientTab[i].method == SOCKET) {
    client.sin_addr.s_addr = htonl(clientTab[i].addr);
    client.sin_port        = htons(clientTab[i].port);
    sendto(isis.sockFD, message, ...);            // ← 슬롯마다 한 번씩
  }
}
```

슬롯 전수 순회이므로 우리 9개 ID가 같은 주소를 가리키면 **같은 데이터그램을 9번 받는다.** 기능상 문제는 없다 — `NodeRouter.resolve` 가 브로드캐스트를 `ICS` 대표로 넘겨 9번 처리하지 않는다. 다만 **수신 트래픽이 9배**다.

`XIS>AL PING` 만은 예외로 두었다 — 재등록의 유일한 경로라서 **9개 ID 전부로 PONG** 해야 한다(⑨). `cmd_ping()` 이 `msg.is_broadcast` 를 보고 분기한다.

> **보강 (2026-08-05) — 우리가 보낸 브로드캐스트도 되돌아온다.** 위 코드는 발신자가 XIS 자신일 때의 경로다. **발신자가 클라이언트일 때**의 경로는 `if (i != sendHost)` 로 **송신 슬롯 하나만** 제외하므로, 시뮬이 `ICS>AL …` 을 쏘면 XIS 가 그것을 **나머지 8개 ID 슬롯 앞으로 되돌려준다.** 전부 같은 (IP,port) 이므로 **자기 발신이 8부 에코된다.**
>
> ③ 의 주석대로였다면(SSO 은퇴 분기) 0부였을 것이다. 운영본은 8부다.
>
> **이게 우리 코드와 만나는 지점이 하나 있다.** `app.py:85` 는 기동 시 9개 ID 각각으로 `<ID>>AL PING` 을 보내고, `commands.py cmd_ping()` 은 **`msg.is_broadcast` 면 발신자가 누구인지 보지 않고** 9개 PONG 을 돌린다. 그런데 XIS 가 그 등록 PING 을 우리 다른 슬롯들로 되돌려주므로, **에코된 자기 PING 이 다시 9개 PONG 을 유발한다.** 등록이 진행될수록 슬롯이 늘어 에코도 함께 늘어난다.
>
> 무한 증폭은 아니다 — PONG 은 `dest=msg.src` 로 **지목 발신**이라 브로드캐스트 분기를 다시 타지 않고, 기동 시 1회의 유한한 버스트로 끝난다. direct-reply 모드(허브 없음)에서는 아예 발생하지 않는다. **그래도 불필요한 버스트이므로 `msg.src` 가 `router.registered_ids` 에 있으면 무시하도록 막는 것이 맞다.** → DevNote 13장 백로그.
>
> ⚠️ **이 경로는 `transport.feed()` 테스트로는 드러나지 않는다.** 에코를 만드는 주체가 XIS 이기 때문이다 — 이 부록 (1)에서 등록 결함이 XIS 경유 모드에서만 드러났던 것과 같은 종류다.

#### ⑦ 함께 확정된 운영 설정 (CTIO `Config/isis.ini`)

```
ServerID   XIS
ServerPort 6660
ServerLog  /lhome/data/Logs/ISIS/isis
TTYPort /dev/ttyS0 115200          ← ICS↔XIS 시리얼 링크, 115200 baud

# Ping the isisrelays on all the IC machines
UDPPort 192.168.14.102 6600  …  .103 .104 .105 .106 .107 .108   (IC 계열 7줄)
# Ping the caliban data-transfer agents only as needed
UDPPort 192.168.14.102 10601 …  .103 .104 .105 .106            (CB 계열 5줄)
# Ping the PC-TCS Agent
UDPPort 192.168.14.108 6606                                     (TC 1줄)

Instrument KMTC
```

- **`.109`(OBS)가 preset 목록에 없다** → (10)절에서 본 `XIS>GMON ERROR: No Route to Destination Host OBS` 가 완전히 설명된다. OBS는 XIS 재시작 후 **자기가 먼저 메시지를 보내기 전까지** 등록되지 않는다. `OBS>XIS PING` 이 하루 2회뿐인 것과 맞물려 실제 공백이 생긴다.
- ICS의 시리얼 링크가 설정으로 확인된다 — `/dev/ttyS0` 115200 baud.

#### ⑧ ~~미해결로 남은 것~~ → **해결됐다 (2026-08-05)** — `MAXPRESET` 은 32 다

<details>
<summary>당시의 서술 (판단 경위를 되짚을 때만 보면 된다)</summary>

`xisisserver.h` 와 `old_isisserver.h` 모두 `#define MAXPRESET 8` 인데 **CTIO `isis.ini` 에는 `UDPPort` 가 13줄**이고, `loadconfig.c` 는 초과분을 명시적으로 버린다:

```c
if (isis.numPreset == MAXPRESET) {
  printf("ERROR: Cannot define more than %d preset UDP socket ports\n", MAXPRESET);
  printf("       extra port ignored.\n");
}
```

8개만 반영된다면 9번째 이후(`M/T/N/G.CB`, `TC`)는 PING을 못 받아야 하는데, **재시작 로그에는 그들도 전부 PONG을 보낸다.** 즉 **배포된 `xisis` 바이너리는 이 백업 소스와 다른 `MAXPRESET` 으로 빌드됐을 가능성이 크다** — `isis.ini` 주석도 "max 32"라고 적혀 있다(헤더는 8).

→ 실물 연동 전에 XIS 콘솔에서 `info` 를 쳐 `NumPreset=? MaxPreset=?` 를 직접 확인할 것.

</details>

**"배포 바이너리가 다른 값으로 빌드됐다"는 추정이 맞았다. 다만 이유가 달랐다** — 다른 값으로 빌드한 것이 아니라 **애초에 다른 트리를 쓰고 있었다.** 운영본 `ISIS/server/isisserver.h` 는:

```c
#define MAXCLIENTS 64   // EXEC_ISIS 와 같음
#define MAXSERIAL  16   // EXEC_ISIS 는 8
#define MAXPRESET  32   // EXEC_ISIS 는 8   ← 이것
```

`isis.ini` 주석의 *"max 16"*(시리얼) · *"max 32"*(preset) 가 **v2.9.1 헤더와 정확히 일치**한다. 로그에서 13개 노드가 전부 PONG 하는 것도 모순 없이 설명된다. 판정 근거 전체는 이 문서 3절.

| | CTIO | SAAO | SSO |
|---|---|---|---|
| 사용 중 `UDPPort` | 13 | 14 | 13 |
| 상한 | 32 | 32 | 32 |
| **여유** | **19** | **18** | **19** |

> **2026-08-11 실물 확인.** SSO AIC 에서 빌드한 XIS 콘솔의 `INFO` 가 `Preset UDP Ports: 2 configured of 32 max` 를 찍었다. 소스 판정에 이어 **상한 32 가 실행 바이너리로 확정**됐다.

→ **신규 `ics` 를 preset 목록에 넣는 데 아무 제약이 없다.** 1안이라 한 줄이면 되고, 설령 2안(9줄)이었어도 여유 안이다. **`info` 실측은 선행 조건이 아니라 확인 절차로 격하된다.**

#### ⑨ 그래서 시뮬은 무엇을 해야 하나

| 항목 | 조치 | 상태 |
|---|---|---|
| 1안 유지 | 소스로 안전 확정. 2안 불필요 | **확정** |
| `bind_host = 0.0.0.0` | IP 브로드캐스트가 아니므로 필수는 아니지만, 외부 연동에는 여전히 필요 | 설정만 바꾸면 됨 |
| **`XIS>AL PING` 에 9개 PONG** | 브로드캐스트 PING 에 9개 노드 ID 전부로 PONG 응답 | **구현 완료 (2026-08-04)** |
| **XIS `isis.ini` 에 시뮬 등록** | `UDPPort <sim_ip> <sim_port>` 한 줄 추가. **1안이라 한 줄이면 된다**(2안이면 9줄 필요) | 운영 측 작업. **⑧ 해결로 선행 조건 없어짐 (2026-08-05)** |
| 주기적 재등록 | preset에 등록되면 필수는 아니나 안전망으로 유효 | 선택 |
| **자기 발신 에코 무시** | ~~`cmd_ping()` 이 `msg.src ∈ registered_ids` 면 응답하지 않도록~~ → **수신 초입 필터로 확대 구현 (2026-08-08).** 유니캐스트 루프백까지 막아야 해서다 — DevNote 3.1.2/12.13 | **완료** |

구현: `commands.py` `cmd_ping()` 이 `msg.is_broadcast` 면 `router.registered_ids` 전부로 PONG 을 보낸다. 지목된 PING(`OBS>K.IC PING`)에는 그 노드로만 답한다.
검증: `test_broadcast_ping_answered_by_all_nine_nodes` · `test_directed_ping_answered_by_that_node_only`.

### (13) 레거시 실제 배치 구조 — VDOS IC + 리눅스 relay (2026-08-04)

같은 백업의 설정 파일들로 **로그만으로는 보이지 않던 물리 구조**가 드러났다. 상세는 [`../ics_legacy/ics_legacy_report.md`](../../ics_legacy/ics_legacy_report.md) 1.3.1절이고, 신규 설계에 걸리는 부분만 옮긴다.

- **IC/ICS 는 VDOS(DOS 계열) 프로그램**이고, **리눅스 호스트 위의 KVM 게스트**에서 돈다(`IC2.img`, `/var/lib/libvirt/images`). 리눅스 `isisrelay` 가 UDP 6600 ↔ 가상 시리얼 9600 으로 중계한다. 로그의 `[192.168.14.102:6600] K.IC>XIS PONG` 은 **relay 가 게스트의 응답을 올려준 것**이다.
- **`TRANSFER DISK<n>` 의 디스크는 게스트에 붙인 가상 디스크**다. 1998년 SCSI 이중버퍼 패턴이 가상화 환경에 그대로 이식돼 살아남았다. 신규는 단일 PC 통합이라 이 계층 자체가 사라진다(DevNote 6.2).
- **`ICS` 는 IC 와 같은 소프트웨어다.** `INSTRUMENT=ICS` 로 설정만 다르고, 프로그램 디렉토리가 `\KMTX`(vs 과학 IC `\KMTS`, 가이드 `\KMTG`)일 뿐이다.
  → **DevNote 5장 메시지 오염 버그가 `ICS` 와 `K.IC` 양쪽에 똑같이 나타나는 이유가 이것이다** — 같은 코드베이스의 단일 결함이다.
- **BUILD 접두어 = 프로그램 디렉토리**: `ICSBUILD=KX…`(\KMTX) · `KBUILD=KS…`(\KMTS) · `GBUILD=KG…`(\KMTG). DevNote 4.3 텔레메트리 꼬리의 정체가 풀렸다.
- **`SP` 노드**(`INSTRUMENT=KMTNsp`, `\KMTS`)가 설정에 존재한다 — 과학 계열 **예비 IC** 로 보이며, XIS preset 의 `192.168.14.107 6600`(로그에 트래픽 0) 자리로 판단된다.

> **신규 설계 함의**: 신규 `ics` 는 이 3계층(VDOS IC + relay + 통합 제어)을 **한 프로그램으로 대체**한다. relay 계층과 시리얼 구간이 통째로 사라지므로 DevNote 5.3 의 전송 손상도 함께 사라진다. **XIS 입장에서는 relay 가 있던 자리에 신규 `ics` 가 들어오는 것으로 보여야 한다** — 그래서 (12)의 등록 규약이 중요하다.
>
> **IC(VDOS) 본체 소스는 이 백업에 없다.** 백업이 리눅스 측(icsci 서버)이라 XIS 서버·relay·Caliban 소스는 있으나 `\KMTS`/`\KMTX`/`\KMTG` 프로그램은 빠져 있다.
>
> **→ `IC2.img` 에서 확보해 읽었다 (2026-08-04). DevNote 5.5 참조.** 여기서 두 가지 예측이 빗나갔다: (a) "역어셈블이 실용적이지 않으니 문자열·포맷 추출까지가 한계"라고 봤는데 **FreeBASIC 소스가 통째로 들어 있어** 그럴 필요가 없었고, (b) "IC 는 C 로 작성됐을 것"이라는 암묵적 전제도 틀렸다. **5장 오염 버그의 코드 위치는 이제 확정됐다**(`PAP7COM.INC:797-802`). 남은 미검토는 `\KMTS`·`\KMTG`(과학·가이드 IC) 쪽이다.

> **1안의 부수 이점이 드러났다**: preset 목록은 (IP, port) 단위라 **단일 소켓이면 한 줄만 추가하면 되고**, 9개 ID가 모두 그 PING을 받아 PONG할 수 있다. 2안이었다면 `MAXPRESET` 을 9줄이나 잡아먹었을 것이고, ⑧의 제약을 감안하면 들어갈 자리가 없었을 수도 있다. (⑧ 이 해결되면서 **2안이었어도 자리는 있었던 것으로 판명**됐다. 1안이 나은 것은 여전하다.)

### (14) 운영 허브 트리 판정 — XISIS 가 아니라 stock ISIS v2.9.1 (2026-08-05)

XIS 자산을 이 폴더 로 따로 정리하면서, **(12) 가 근거로 삼은 트리가 운영본이 아니라는 것**이 드러났다. 판정 근거 6가지와 재빌드 방법은 이 문서 3~4절 에 있고, 여기에는 **신규 `ics` 설계에 걸리는 것만** 옮긴다.

| 트리 | 산출물 | 버전 | 정체 |
|---|---|---|---|
| `ISIS/` | `isis` (+`isisd`, +`isisrelay`) | **2.9.1** | **운영본.** `Config/isis.ini` 의 `ServerID XIS` 로 기동된다 |
| `EXEC_ISIS/` | `xisis` | 2.7.3 | J. Mason(OSU ISL)의 KMTN 전용 분기, 2014-02~08. **은퇴** |
| `ISIS_V1/` | `isis` | 2.7.3 | 구버전 백업 |

**`XIS` 는 프로그램 이름이 아니라 노드 ID다.** 이름이 비슷해 `EXEC_ISIS`(XISIS)를 운영본으로 읽었던 것이 (12) 의 출발점이었다.

**설계에 걸리는 세 가지**

1. **`MAXPRESET` 은 32** — ⑧ 해결. 시뮬 등록에 제약 없다.
2. **브로드캐스트는 송신 슬롯 하나만 제외한다** — ⑥ 보강. 우리 발신이 8부 에코된다.
3. **`EXEC_ISIS` 의 방어 코드가 운영본에는 없다.** CTIO `EXEC_ISIS/server/interfaces.c` 에는 *"srcID 가 serverID 와 같으면 메시지를 버리고 경고를 남긴다"* 는 2014-09-30 자 패치가 있는데(`WARNING: Anomalous socket host srcID=%s same as serverID=%s`), **v2.9.1 에는 없다.** 신규 `ics` 가 실수로 `XIS` 를 발신 ID 로 쓰면 **운영 허브는 걸러 주지 않는다.** 발신 ID 검증은 우리 쪽 책임이다.

**부수적으로 확인된 것**

- **운영 서버 소스는 3사이트 바이트 동일**하다(CTIO = SAAO, SSO 는 `relay/` 두 파일만 다름). 사이트별 서버 분기를 걱정할 필요가 없고, **사이트 차이는 전부 `isis.ini` 에 있다**(⑦, (11)).
- 콘솔에 **`UDPPING <ip> <port>`** 명령이 있다 → **preset 목록에 넣기 전에도 XIS 콘솔에서 직접 PING 을 쏴 우리 등록을 시험할 수 있다.** 실물 연동 1단계가 운영 설정 변경 없이 가능해진다.
- **운영 바이너리(`isis` v2.9.1)는 백업에 없다.** 소스와 빌드 스크립트는 온전하므로 재빌드가 전제다(`g++`·`readline`·`ncurses`). 보관된 ELF 2개는 은퇴한 `xisis` 빌드다.

### (11) 함께 확인된 포트 설정

| 키 | 현재 값 | 비고 |
|---|---|---|
| `bind_host` | `127.0.0.1` | **로컬 전용.** 외부 XIS/OBSAgent와 붙이려면 `0.0.0.0` 으로. XIS가 재시작 시 IP 서브넷 브로드캐스트로 PING을 뿌린다면((9)절) `0.0.0.0` 이 **필수**다 — 아니면 재등록 기회를 놓친다 |
| `bind_port` | `6600` | 레거시 IC 계열 관례 포트. 실제 배치의 ICS는 시리얼이라 정해진 UDP 포트가 없어 임의로 고른 값이다. **같은 호스트에 실제 `K.IC` 가 떠 있으면 충돌** |
| `xis_host` | (빈 값) | 비어 있어 **direct-reply 모드가 기본**. 이 모드에서는 (1)의 등록 문제가 드러나지 않는다 |
| `xis_port` | `6660` | CTIO 기준 (OBSAgent `ISISPort 6660`) |
