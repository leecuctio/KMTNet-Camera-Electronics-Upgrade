# MANIFEST — XIS 보관본 파일 목록과 출처

이 폴더의 모든 파일은 **원본을 그대로 복사**한 것이다(파일명·내용 무변경). 배경과 판단은 [xis.md](xis.md) 를 본다.

**원본 위치**: `ics_legacy/__dts_legacy/dts.icsci.20190326.{ctio,saao,sso}/dts.icsci/`
— ICS 컴퓨터(`icsci` 서버)의 `/home/dts` 폴더를 사이트별로 백업한 것. 2019-03-26 시점.

**무결성**: [SHA256SUMS.txt](SHA256SUMS.txt) 에 보관 원본 **162개 파일 전체**의 SHA256 이 있다(이번에 새로 만든 파일 5개는 제외).

```bash
cd ics_sim/xis && sha256sum -c SHA256SUMS.txt
```

---

## 파일 배치와 출처

| 이 폴더 | 원본 경로 | 파일 | 비고 |
|---|---|---|---|
| `src/` | `ctio/…/ISIS/` | 95 | **운영 중인 허브의 소스** (ISIS v2.9.1). CTIO 트리 전체 |
| `install/config/<site>/isis.ini` | `<site>/…/Config/isis.ini` | 3 | **사이트별 운영 설정.** `ServerID XIS` |
| `install/scripts/common/` | `ctio/…/bin/` | 3 | `startisis` · `stopisis` · `chkisis`. 3사이트 동일 |
| `install/scripts/<site>/KMTN_Startup_ICS` | `<site>/…/bin/` | 3 | 사이트마다 다름 |
| `tools/isisPerl/` | `ctio/…/isisPerl/` | 3 | `00README` · `00NOTES` · `ISIS.pm`. 3사이트 동일 |
| `tools/isisPerl/<site>/` | `<site>/…/isisPerl/` | 6 | `isisCmd` · `execISIS`. 사이트마다 다름 |
| `branches/xisis-2.7.3/` | `ctio/…/EXEC_ISIS/` | 45 | **은퇴한 XISIS 분기.** doxygen 생성 HTML 제외 |
| `branches/xisis-2.7.3/site-deltas/` | `saao`·`sso/…/EXEC_ISIS/server/` | 4 | 위 분기에서 사이트별로 갈리는 소스만 |

`SHA256SUMS.txt` · `.gitignore` · `.gitattributes` · `xis.md` · `MANIFEST.md` 는 이번에 새로 만든 파일이다. `.gitattributes` 는 git 의 줄끝 정규화를 꺼서(`* -text`) 보관 원본의 바이트와 SHA256 검증을 보전한다.

## `src/` 안쪽

| 경로 | 내용 |
|---|---|
| `src/00README.txt` · `RELEASE` | 상위 패키지 설명 (R. Pogge) |
| `src/server/` | **허브 서버 소스.** `main.c` · `interfaces.c` · `messages.c` · `clients.c` · `commands.c` · `loadconfig.c` · `serverlog.c` · `utils.c` · `isisserver.h` · `isisd.c`(데몬판) |
| `src/server/Makefile.build` · `build` | 빌드 정의(v2.9.1)와 빌드 스크립트 |
| `src/server/daemon/isisd.init` | SysV init 스크립트 (데몬 모드용, KMTNet 은 미사용) |
| `src/server/doc/html/` | 서버 doxygen 문서 (생성물) |
| `src/client/` | ISIS 클라이언트 라이브러리 `libisis.a` 소스 + doxygen |
| `src/relay/` | **`isisrelay` 소스.** IC 머신에서 UDP 6600 ↔ 시리얼을 중계하는 프로그램 |
| `src/doc/ICIMACS2.txt` | ICIMACS(IMPv2) 프로토콜 정의 |
| `src/doc/ISIS_commands.txt` | ISIS 명령 세트 문서 |
| `src/config/` · `src/server/examples/` | 배포 시점 `.ini` 템플릿 |

> ⚠️ `src/` 안의 `.ini` 는 **배포 시점 템플릿**이다. `src/config/isis.ini` 와 `src/server/isis.ini` 는 2014-10-21 자 SSO 주소본이고, `src/relay/isisrelay.ini` 도 SSO 주소(192.168.15.109)를 담고 있다. **운영 실물은 `install/config/` 를 볼 것.**

## 사이트 간 동일성 (검증 결과)

| 대상 | CTIO | SAAO | SSO |
|---|---|---|---|
| `ISIS/` 트리 (= `src/`) | 기준 | **바이트 동일** | `relay/Makefile` · `relay/main.c` 만 다름. **서버 소스는 동일** |
| `Config/isis.ini` | 192.168.14.x · `KMTC` · preset 13줄 | 192.168.13.x · `KMTS` · preset 14줄 | 192.168.15.x · `KMTA` · preset 13줄 |
| `KMTN_Startup_ICS` | 다름 | 다름 | 다름 (셋 다 `/home/dts/ISIS/server/isis` 기동) |
| `startisis`·`stopisis`·`chkisis` | 기준 | 동일 | 동일 |
| `isisPerl/isisCmd` | `.14.109:6660` `XIS` | **미현지화** (`172.16.1.240:6600` `IS`) | v1.0.4K · `.15.109:6660` `XIS` |
| `isisPerl/execISIS` | 미현지화 | 미현지화 | v0.3.0K · 현지화됨 |
| `EXEC_ISIS/` (은퇴 분기) | `interfaces.c` 가 최신(2014-09-30 패치) · **실행파일 2종 보유** | `interfaces.c` 구버전 | `interfaces.c` 구버전 + `messages.c` 자체 패치 |

## 실행 파일

`branches/xisis-2.7.3/server/` 안의 두 ELF 는 **은퇴한 XISIS 분기의 빌드 산출물**이다. 운영 중인 `isis` 바이너리는 이 백업에 없다 ([xis.md](xis.md) 4절).

| 파일 | 빌드일 | SHA256 (앞 16) | 비고 |
|---|---|---|---|
| `xisis.last` | 2014-Jul-31 | `74c5d6ec5d032a16` | 마지막 XISIS 빌드 |
| `old.xisis` | 2014-Feb-19 | `cceb7d984944c656` | 그 이전 빌드 |

둘 다 ELF 64-bit LSB executable, x86-64, `GCC 4.4.7 20120313 (Red Hat 4.4.7-4)` — RHEL/CentOS 6 계열에서 빌드됐다. 컴파일 시점 기본 설정 경로는 `/lhome/dts/Config/xisis.ini`, 로그는 `/lhome/data/Logs/XISIS/xisis`, 버전 문자열은 `2.7.3`.

## 일부러 안 가져온 것

| 대상 | 원본 위치 | 이유 |
|---|---|---|
| `ISIS_V1/` | `<site>/…/ISIS_V1/` | ISIS v2.7.3 구버전 백업. `MAXCLIENTS 32`·`MAXPRESET 8`·`MAXSERIAL 8`. 운영과 무관 |
| `EXEC_ISIS/*/doc/html/` | `<site>/…/EXEC_ISIS/` | doxygen 생성물이고 `src/` 쪽과 거의 같은 내용 |
| `Config/OLD/` · `Config/Version1/` · `Config_V1/` | `<site>/…/` | 은퇴한 설정 세대 |
| ISIS 클라이언트 라이브러리 사본 | `TCSAgent/__reference/ISISclient/` · `OBSAgent/OBSAgent.latest/ISISclient/` | 이미 각 폴더에 있다. `src/client/` 와 별개 계보 |
| `Agents/` · `Utilities/` · `cortable/` · `VMFolder/` | `<site>/…/` | XIS 범위 밖 (caliban·pctcs·XTV·VM 이미지 설정 등) |

원본은 전부 `ics_legacy/__dts_legacy/` 에 그대로 남아 있다.
