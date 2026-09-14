# ACF 설치 대장 — 어느 사이트 어느 상자에 **어느 판**이 깔려 있나

**되돌릴 목표를 적어 두는 한 장**이다 (2026-09-14 신설, 운영자 지시 — DevNote 11.86-(10) #10 ·
11.85-(6) 끝줄 *"굽기 전에 한 장으로 세울 것"*).  판을 굽는 것과 판을 **까는** 것은 다른 일이고,
저장소 `acf/` 는 앞쪽만 안다.  이 문서가 뒤쪽을 적는다.

⛔ **여기서는 판을 번호로 부르지 않는다 — 파일명 전체로 적는다.**  판 번호는 계열별이라
(`R2608`~`R2613` 이 guide·science 양쪽에 다 있다) 번호만으로는 어느 계열인지 갈리지 않는다.
파일명(`KMT?_SCI_…`/`KMT?_GUI_…`)에는 계열이 박혀 있어 모호성이 원천에서 막힌다.
같은 이유로 **벤치에 판을 지시할 때도 파일명 전체로** (`acf/README.md` 머리의 규칙 셋).

## "깔려 있다" 의 뜻

Archon 은 설정을 **비휘발로 갖고 있지 않다.**  호스트(`ics_archon`/`icg_archon`)가 **기동마다**
ini 가 가리키는 ACF 를 `CLEARCONFIG → WCONFIG → APPLYALL` 로 밀어 넣는다 (`apply_acf` 눈금은
2026-09-12 에 걷었다 — DevNote 11.82).  그래서

    깔린 판  =  그 사이트 호스트의 ~/AIC/Config/acf/ 에 있는 파일 중
                ~/AIC/Config/ics_archon.ini  [archon] acf_mk / acf_nt
                ~/AIC/Config/icg_archon.ini  [icg] acf
                가 가리키는 것

이지, 컨트롤러 메모리에 지금 앉아 있는 것이 아니다 (그것은 다음 기동에서 덮인다).
⭐ **확인하는 법 둘**: ① 그 호스트 ini 의 위 세 줄 ② 그 호스트가 찍은 프레임의 `CTRLnCFG`
헤더 — 파일명이 폴더·확장자만 뗀 채 그대로 찍힌다 (`config.cfg_name_from_acf`, 규격 5.5절).
⛔ **저장소를 `git pull` 해도 현장은 안 바뀐다** — `~/AIC/Config/acf/` 로 복사하고 ini 줄을
손으로 고쳐야 한다 (`INSTALL.md`).  그 손질을 한 날이 이 대장에 적힐 날이다.

## 상자 — 신원 (바뀌지 않는 것)

ACF 의 `BACKPLANE_ID`·`BACKPLANE_REV`·`BACKPLANE_VERSION`·`IP` 에서 그대로 읽었다
(2026-09-14, 현행 열두 장 = 2026-09-11 반입분과 **전부 동일**).  유닛↔시리얼 정본은
`../../raw_fits_spec/__reference/Archon_Unit_Info.txt`.

| 사이트 | 유닛 | 시리얼 | `BACKPLANE_ID` | IP | REV · FW(최종판) | 비고 |
|---|---|---|---|---|---|---|
| CTIO | `KMTC-SCI-101` (MK) | STA0284 | `…1F606B92` | `10.0.0.101` | 7(Rev H) · `1.0.1271` | 2026-09-11 에 `MOD2`(드라이버) 모듈이 갈렸다 |
| CTIO | `KMTC-SCI-102` (NT) | STA0285 | `…1F60AAA4` | `10.0.0.102` | 7 · `1.0.1271` | |
| CTIO | `KMTC-GUI-161` | STA0290 | `…1F602266` | `10.0.0.161` | 7 · `1.0.1271` | |
| SAAO | `KMTS-SCI-101` (MK) | STA0286 | `…1F6033DF` | `10.0.0.101` | 7 · `1.0.1271` | |
| SAAO | `KMTS-SCI-102` (NT) | STA0287 | `…1EE27A29` | `10.0.0.102` | 7 · `1.0.1271` | |
| SAAO | `KMTS-GUI-161` | STA0291 | `…1F60839C` | `10.0.0.161` | 7 · `1.0.1271` | |
| KASI 벤치 | `KMTK-SCI-113` (MK+NT **한 상자**) | STA0200 | `…1A708986` | `10.0.0.113` | 5(Rev F) · `1.0.1252` | MK/NT 두 ACF 가 같은 상자를 가리킨다 |
| KASI 벤치 | `KMTK-SCI-112` (MK+NT **한 상자**) | STA0212 | `…1A7068D5` | `10.0.0.112` | 5 · `1.0.1252` | 2026-09-11 신규 |
| KASI 벤치 | `KMTK-GUI-162` | STA0201 | `…1A99369B` | `10.0.0.162` | 5 · `1.0.1252` | ⛔ 아래와 **같은 IP** — 동시에 못 띄운다 |
| KASI 벤치 | `KMTK-GUI-162` (둘째) | STA0230 | `…1A9939ED` | `10.0.0.162` | 5 · `1.0.1252` | 2026-09-11 신규.  붙은 쪽은 `BACKPLANE_ID` 로 가린다 |
| SSO | `KMTA-SCI-101` | STA0288 | ⏳ | ⏳ | ⏳ | ⛔ **ACF 가 아직 없다** |
| SSO | `KMTA-SCI-102` | STA0289 | ⏳ | ⏳ | ⏳ | 〃 |
| SSO | `KMTA-GUI-161` | STA0292 | ⏳ | ⏳ | ⏳ | 〃 |

⚠️ IP 가 사이트를 넘어 겹치는 것은 정상이다 (사이트마다 내부망).  ⛔ **보드 판에 맞는 FW 만
굽는다** — `1.0.1271` 은 Rev H 의 최종판이지 Rev F 보다 새 판이 아니다 (`README.md` 표).

## 판 — 저장소 현행 vs 현장에 마지막으로 확인된 것 (**여기가 대장이다**)

| 상자 | 저장소 **현행** (`acf/`) | 현장에 **마지막으로 확인된** 판 | 확인일 · 근거 | 격차 |
|---|---|---|---|---|
| CTIO SCI-101 | `KMTC_SCI_101_STA0284_R2613_MK.acf` | `KMTC_SCI_101_STA0284_R2611_MK.acf` | 2026-09-11 · 초기화 시험 반입 ① | science 2판 |
| CTIO SCI-102 | `KMTC_SCI_102_STA0285_R2613_NT.acf` | `KMTC_SCI_102_STA0285_R2611_NT.acf` | 〃 | science 2판 |
| CTIO GUI-161 | `KMTC_GUI_161_STA0290_R2622.acf` | `KMTC_GUI_161_STA0290_R2619.acf` | 〃 | guide 3판 |
| SAAO SCI-101 | `KMTS_SCI_101_STA0286_R2613_MK.acf` | `KMTS_SCI_101_STA0286_R2611_MK.acf` | 〃 | science 2판 |
| SAAO SCI-102 | `KMTS_SCI_102_STA0287_R2613_NT.acf` | `KMTS_SCI_102_STA0287_R2611_NT.acf` | 〃 | science 2판 |
| SAAO GUI-161 | `KMTS_GUI_161_STA0291_R2622.acf` | `KMTS_GUI_161_STA0291_R2619.acf` | 〃 | guide 3판 |
| KASI SCI-113 | `KMTK_SCI_113_STA0200_R2613_{MK,NT}.acf` | `KMTK_SCI_113_STA0200_R2611_{MK,NT}.acf` | 〃 · ⏳ 벤치 ini 실값 미확인 ② | science 2판 |
| KASI SCI-112 | `KMTK_SCI_112_STA0212_R2613_{MK,NT}.acf` | `KMTK_SCI_112_STA0212_R2611_{MK,NT}.acf` | 〃 | science 2판 |
| KASI GUI-162 (STA0201) | `KMTK_GUI_162_STA0201_R2622.acf` | `KMTK_GUI_162_STA0201_R2619.acf` | 〃 · ⏳ ② | guide 3판 |
| KASI GUI-162 (STA0230) | `KMTK_GUI_162_STA0230_R2622.acf` | `KMTK_GUI_162_STA0230_R2619.acf` | 〃 | guide 3판 |
| SSO 셋 | — (ACF 없음) | — | — | — |

① `__ref_archon_control/acf_20260911/` — 2026-09-11 각 유닛 초기화 시험에서 **GUI 가 각 상자에
붙어 저장한** 열두 장.  `BACKPLANE_VERSION`·`MODn_VERSION`·`MOD2_ID` 같은 **컨트롤러가 보고한 값**이
들어 있어 *"그때 그 상자에 적용된 설정"* 의 기록이다.  타이밍 스크립트는 열두 장 전부
`acf_timing_script_science_R2611.txt` / `acf_timing_script_guide_R2619.txt` 와 **바이트 동일**
(`tools/extract_timing_script.py`).
② KASI 벤치 호스트(`kmtnet-sso`)의 `~/AIC/Config/*.ini` 실값은 이 저장소에서 안 보인다.
저장소 `icg_archon.ini` 의 `[icg] acf` 는 `…_STA0201_R2622.acf` 를 가리키지만 **그것은 저장소
쪽 기본값**이지 벤치에 복사됐다는 뜻이 아니다.  ⏳ **운영자 기입**.

### ⛔ 읽는 법 — 현장과 저장소가 **다섯 판** 벌어져 있다

2026-09-11 이후 저장소는 science 둘(`R2612`·`R2613`) · guide 셋(`R2620`·`R2621`·`R2622`)을 더
구웠고 **현장에 깐 기록은 0건**이다.  그 다섯 판이 무엇을 바꿨는지는 `README.md` 의 각 절.
⭐ 그중 **파형이 바뀐 것**은 `guide R2622`(`FlushFrame:` 119행 `DGHIGH`) 하나이고, 나머지 넷은
파라미터 슬롯 순서·상수 이름·제어 흐름이다.  ⚠️ 그 전에도 **`guide R2614`·`R2615` 의 파형
델타는 벤치 확인 기록이 없다** (DevNote 11.84-(6)) — 2026-09-11 반입분(`R2619`)에 **이미 들어
있는** 채로 현장에 있다.

⛔ **되돌릴 목표는 이 표의 "마지막으로 확인된" 열**이다.  벤치에서 사다리(`acf/bench/`)를 올리다
멈추면 돌아갈 곳은 *"저장소 현행"* 이 아니라 **그 상자에 마지막으로 깔렸던 파일**이다 —
사다리 `T0` 가 `R2612` 내용인데 벤치 상자는 `R2611` 로 기록돼 있으니, 사다리를 시작하기 전에
② 를 먼저 채울 것.

## 이력 (덧붙이기만 한다 — 위 표는 이 이력의 마지막 줄이다)

| 날짜 | 어디 | 무엇을 깔았나 (파일명 전체) | 누가 · 근거 |
|---|---|---|---|
| 2026-09-11 | CTIO 3 · SAAO 3 · KASI 6 (열두 장) | `KMT?_SCI_*_R2611_{MK,NT}.acf` 8장 · `KMT?_GUI_*_R2619.acf` 4장 | 운영자 · 각 유닛 초기화 시험, `acf_20260911/` 반입.  관측소 상자 FW `1.0.1261`→`1.0.1271` 도 이때 |
| 2026-09-12~14 | (저장소만) | science `R2612`·`R2613` · guide `R2620`·`R2621`·`R2622` 구움 | 세션 32~35 · **현장 반영 0** |

## 갱신 절차

**판을 구운 세션**은 "저장소 현행" 열만 고친다 (파일명 전체로).  **현장에 깐 사람**은
"마지막으로 확인된" 열 + 확인일·근거 + 이력 한 줄을 적는다 — 근거는 ini 줄이거나 그 뒤 첫
프레임의 `CTRLnCFG` 값.  ⛔ 벤치에서 `acf/bench/` 사다리를 올린 것도 이력에 적는다 (꼬리표
`_T0`~`_T4` 까지 파일명 전체로) — 되돌릴 때 어디로 가야 하는지가 그 줄이다.

## ⏳ 운영자가 채울 것

1. ② — 벤치 호스트 `~/AIC/Config/ics_archon.ini`·`icg_archon.ini` 의 `acf` 세 줄 실값과
   `~/AIC/Config/acf/` 목록 (`ls ~/AIC/Config/acf/ && grep -n '^acf' ~/AIC/Config/*.ini`).
2. 관측소 상자 여섯이 **지금 어디 있나** (KASI 조립장 / 사이트) — 초기화 시험을 어디서 했는지.
3. SSO 세 상자의 `BACKPLANE_ID`·REV·FW — ACF 가 반입되면 이 표와 `README.md` 목록을 함께 채운다.
