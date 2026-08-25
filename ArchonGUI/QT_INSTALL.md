# ArchonGUI 빌드 — Qt5 설치

STA 가 준 Archon 컨트롤러 GUI(**ArchonGUI**)를 리눅스에서 빌드할 때의 Qt 설치
절차다.  2026-08-24 `kmtnet-sso`(SSO) 에서 실측했다.

⚠️ **ArchonGUI 는 이 저장소의 프로그램이 아니다.**  기계에서 따로 풀려 있고
(`~/CEU/ArchonGUI/archongui_v1.0.1259.KMTNet_20260118_SSO`) `ics_archon` 과 코드를
공유하지 않는다.  같은 기계에 함께 서고, 컨트롤러를 손으로 만질 때 쓰므로 여기에
적어 둔다.

## 한 줄 처방

```bash
sudo apt install build-essential qt5-qmake qtbase5-dev qtbase5-dev-tools libqt5svg5-dev
```

`Unknown module(s) in QT: core gui widgets ...` 는 **Qt 가 없다는 뜻이 아니라 개발
패키지가 없다는 뜻**이다.

---

## 0. 증상

두 가지가 짝으로 나온다.

```
$ make release
/usr/lib/qt5/bin/qmake -o Makefile archongui.pro
Project ERROR: Unknown module(s) in QT: core gui widgets network concurrent svg
make: *** [Makefile:151: Makefile] Error 3

$ qmake -query
qmake: could not find a Qt installation of ''
```

**둘은 원인이 다르다.**

| 증상 | 무엇 |
|---|---|
| `Unknown module(s) in QT` | `/usr/lib/qt5/bin/qmake` 는 **실제 바이너리이고 잘 돌았다.**  모듈 정의 파일 `mkspecs/modules/qt_lib_*.pri` 가 없다 → **개발 패키지 부재** |
| `could not find a Qt installation of ''` | `/usr/bin/qmake` 는 실제 qmake 가 아니라 **qtchooser** 로 가는 심링크다.  기본 Qt 가 지정되어 있지 않다 → `QT_SELECT` |

⚠️ **`make debug` 도 똑같이 죽는다.**  Makefile 을 만드는 qmake 단계에서 걸리므로
타깃과 무관하다.  `readme.txt` 가 안내하는 `qmake archongui.pro` 를 손으로 쳐도
같다.

> **`core`·`gui` 까지 전부 unknown 이면 모듈 이름을 하나씩 의심할 일이 아니다.**
> 그 둘은 Qt 의 가장 기본 모듈이라, 안 보인다는 것은 특정 모듈이 빠진 것이 아니라
> **모듈 정의 폴더가 통째로 없다**는 뜻이다.

## 1. 진단

맨 `qmake` 는 qtchooser 때문에 못 쓰므로 **실제 경로**로 묻는다.

```bash
/usr/lib/qt5/bin/qmake -query QT_INSTALL_PREFIX QT_HOST_DATA QT_VERSION
ls "$(/usr/lib/qt5/bin/qmake -query QT_HOST_DATA)/mkspecs/modules/" | head
qtchooser -l
dpkg -l | grep -E 'qtbase5|qt5-qmake|libqt5svg5'
```

- `mkspecs/modules/` 가 **없거나 비어 있으면** 개발 패키지 부재로 확정이다
- `dpkg` 목록에 런타임(`libqt5core5a` 등)만 있고 `qtbase5-dev` 가 없으면 같은 결론
- `/opt/Qt*` · `~/Qt*` 에 별도 설치본이 있으면 그 qmake 를 직접 쓰는 것으로 끝난다.
  **그때는 아무것도 설치할 필요가 없다** — 반드시 이것부터 볼 것

## 2. 설치

⚠️ **운영 장비다.**  `apt remove` · `purge` 로 Qt 를 걷어내면 거기 링크된 다른
소프트웨어까지 딸려 나간다.  **덧붙이기만 한다.**  이미 깔린 것을 새로 덮고 싶으면
제거가 아니라 `sudo apt install --reinstall <패키지>` 다.

먼저 시뮬레이션한다 — `-s` 라서 아무것도 건드리지 않는다.

```bash
sudo apt install -s build-essential qt5-qmake qtbase5-dev qtbase5-dev-tools libqt5svg5-dev
```

출력에 `REMV`(지움) 줄이 하나라도 있으면 **거기서 멈춘다.**  설치만 뜨면 그대로
진행한다.

```bash
sudo apt update
sudo apt install build-essential qt5-qmake qtbase5-dev qtbase5-dev-tools libqt5svg5-dev
```

| 패키지 | 무엇을 채우나 |
|---|---|
| `build-essential` | `g++`·`make` (대개 이미 있다) |
| `qt5-qmake` | qmake 본체 |
| `qtbase5-dev` | **`core`·`gui`·`widgets`·`network`·`concurrent`** 헤더 + `mkspecs` |
| `qtbase5-dev-tools` | `moc`·`uic`·`rcc` — Qt 빌드 필수 도구 |
| `libqt5svg5-dev` | **`svg`** — qtbase 에 없는 유일한 모듈 |

`archongui.pro` 가 요구하는 6 개 모듈이 이것으로 다 채워진다.

> `dnf` 계열이면 `qt5-qtbase-devel qt5-qtsvg-devel` 이다.  `cat /etc/os-release`
> 로 확인하고 고른다.

## 3. 확인

```bash
export QT_SELECT=qt5
qmake -query QT_VERSION
ls "$(qmake -query QT_HOST_DATA)/mkspecs/modules/" | grep -E 'core|svg|concurrent'
```

2026-08-24 `kmtnet-sso` 실측: `5.15.13`, `qt_lib_core.pri` ·
`qt_lib_concurrent.pri` · `qt_lib_svg.pri` 확인.

⚠️ **`QT_SELECT` 은 셸 세션마다 필요하다.**  자주 빌드할 기계면 `~/.bashrc` 에
`export QT_SELECT=qt5` 한 줄을 넣는다.  안 넣으면 맨 `qmake` 가 다시
`could not find a Qt installation of ''` 로 죽는다.

## 4. 빌드

```bash
cd ~/CEU/ArchonGUI/archongui_v1.0.1259.KMTNet_20260118_SSO
rm -f Makefile && qmake archongui.pro && make release -j4
```

실행 파일은 `release/` 에 생긴다(`readme.txt` 기준, `debug` 는 `debug/`).

### `Nothing to be done for 'first'` 가 나오면

```
make -f Makefile.Release
make[1]: Nothing to be done for 'first'.
```

배포본에 **예전 빌드 산출물이 들어 있다.**  `.o` 와 실행 파일의 타임스탬프가
원본보다 새로워서 make 가 「이미 최신」으로 판정한 것이다.

⚠️ **먼저 그 산출물이 그냥 도는지 본다.**  2026-08-24 SSO 실측에서는 **기존
`release/` 산출물이 정상 기동했다** — 개발 패키지를 깔면서 부족했던 런타임 의존이
같이 채워진 것으로 보인다.  이 경우 **재빌드가 필요 없다.**

```bash
ls -la release/
./release/archongui        # 실행 파일 이름은 ls 로 확인
```

정말 새로 컴파일해야 할 때만:

```bash
cp -a release release.bak                          # 되돌릴 자리를 먼저 만든다
make -f Makefile.Release clean && make release -j4
```

그래도 안 돌면 통째로 밀고 간다.

```bash
rm -rf release Makefile Makefile.Release Makefile.Debug
qmake archongui.pro && make release -j4
```

---

## 이상할 때

| 증상 | 원인·처방 |
|---|---|
| `Project ERROR: Unknown module(s) in QT: core gui …` | 개발 패키지 부재 → **2. 설치**.  모듈 이름을 하나씩 좇지 말 것 |
| `qmake: could not find a Qt installation of ''` | qtchooser 기본값 없음 → `export QT_SELECT=qt5`, 또는 `/usr/lib/qt5/bin/qmake` 를 직접 부른다 |
| `make debug` 도 같은 에러 | 정상이다 — qmake 단계에서 죽으므로 타깃과 무관 |
| `Nothing to be done for 'first'` | 예전 산출물이 남아 있다 → 위 절 참조.  **지우기 전에 실행부터 해 볼 것** |
| `Makefile:151: Makefile] Error 3` | Makefile 이 스스로를 다시 만들려고 qmake 를 부른 것이다.  진짜 원인은 그 위의 `Project ERROR` 줄 |
| `(END)` 에서 안 빠져나온다 | git 등이 띄운 페이저(`less`)다 → `q` |

## 왜 이런가

| 무엇 | 성질 |
|---|---|
| 개발 패키지 분리 | 데비안 계열은 런타임(`libqt5core5a` …)과 빌드용 헤더·`mkspecs`(`qtbase5-dev`)를 **다른 패키지로 나눠 담는다.**  다른 Qt 프로그램이 잘 돌고 있어도 빌드는 안 된다 |
| `QT +=` 의 해석 | qmake 는 `.pro` 의 `QT += core gui …` 를 `mkspecs/modules/qt_lib_<이름>.pri` 로 푼다.  그 폴더가 없으면 **모든** 이름이 unknown 이 된다 |
| qtchooser | `/usr/bin/qmake` → `qtchooser` 심링크.  어느 Qt 를 쓸지 `QT_SELECT` 나 `default.conf` 로 정해야 한다.  비어 있으면 `''` 를 찾다가 실패한다 |
| `svg` 만 따로 | `core`·`gui`·`widgets`·`network`·`concurrent` 는 qtbase 한 덩어리이고, `svg` 는 별도 모듈(`libqt5svg5-dev`)이다 |

## 미확인

| 항목 | 상태 |
|---|---|
| Qt 5.15 로 **처음부터 다시 컴파일**해서 끝까지 가는지 | ❌ **미확인.**  `readme.txt` 는 **Qt 5.2** 기준이다.  SSO 에서는 기존 산출물이 그냥 돌아서 전체 재빌드를 강행하지 않았다 — 5.2→5.15 사이 deprecated API 로 걸릴 여지가 남아 있다 |
| 배포판 | 미기록.  `/etc/os-release` 를 확인하지 않았다.  `apt`·`qtchooser` 를 쓰므로 데비안 계열이고 Qt 는 `5.15.13` 이다 |
| CTIO · SAAO 기계 | ❌ 미확인.  SSO 에서만 실측했다 |
| `~/.bashrc` 의 `QT_SELECT` 영구 등록 | 하지 않았다.  현재는 셸마다 손으로 넣어야 한다 |

## 관련 문서

| 문서 | 무엇 |
|---|---|
| [INSTALL.md](INSTALL.md) | 벤치 설치 — `~/AIC` 한 벌 세우기.  **C 프로그램 셋의 의존 패키지는 그쪽** |
| [README.md](README.md) | `ics_archon` 구성 · 설정 · 실기 첫 실행 |
| [SMC_CLAUDE.md](SMC_CLAUDE.md) | 인수인계 — 결정사항 · Archon 매뉴얼 확정 사실 |
