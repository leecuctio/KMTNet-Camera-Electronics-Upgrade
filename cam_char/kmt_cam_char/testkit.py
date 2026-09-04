"""Synthetic L0 amp-MEF fixtures for kmt_cam_char tests (no real data needed).

Builds small-geometry mock64-style MEF files that `core.open_l0` /
`roi_raw` / `ovsc_raw` read unmodified, with hooks to inject the effects
the new analysis modules must detect: per-amp gain/RN/bias, shot noise,
nonlinearity, periodic pickup, controller-shared common-mode noise, ADC
code defects (missing code / stuck bit), persistence, saturation.

Geometry is reduced (default 8 amps, 200 data + 32 real-overscan +
16 mirrored cols x 320 rows), so every analysis function must accept
``roi``/``ovsc`` slice overrides (production defaults: `core.ROI`,
`core.OVSC_REAL`).  Use ``kit.roi`` / ``kit.ovsc`` in tests.

Typical use:
    kit = SynthL0(tmpdir, seed=1)
    p = kit.frame("b0001", level_adu=0)                       # bias
    p = kit.frame("f0001", level_adu=20000, exptime=10.0)     # flat
    with core.open_l0(p) as exp: ...
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from astropy.io import fits

# 축소 지오메트리 기본값 (프레임당 ~1.2 MB, 64앰프 실물 대비 1/600)
N_AMPS = 8
NY = 320
DATA_COLS = 200
OVSC_COLS = 32          # real overscan (core.OVSC_REAL 대응)
MIRROR_COLS = 16        # mock 형식의 거울 복제 꼬리 (통계 사용 금지 영역)

_CHIPS = ("M", "K")     # 앞 절반 ctrl 1 / 뒤 절반 ctrl 2


def _sec(x1, x2, y1, y2):
    return "[%d:%d,%d:%d]" % (x1, x2, y1, y2)


class SynthL0:
    """작은 L0 MEF 생성기. 앰프별 파라미터와 결함 주입 훅을 제공한다."""

    def __init__(self, outdir, namps=N_AMPS, ny=NY, data_cols=DATA_COLS,
                 ovsc_cols=OVSC_COLS, mirror_cols=MIRROR_COLS, seed=0,
                 gain=1.46, rdnoise_adu=3.5, bias_adu=1000.0):
        self.outdir = Path(outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.namps, self.ny = int(namps), int(ny)
        self.data_cols, self.ovsc_cols = int(data_cols), int(ovsc_cols)
        self.mirror_cols = int(mirror_cols)
        self.nx = self.data_cols + self.ovsc_cols + self.mirror_cols
        self.rng = np.random.default_rng(seed)
        # 분석 함수에 넘길 축소 ROI/overscan 슬라이스 (여유 마진 포함)
        self.roi = (slice(20, self.ny - 20), slice(10, self.data_cols - 10))
        self.ovsc = slice(self.data_cols, self.data_cols + self.ovsc_cols)
        # 앰프별 파라미터 (테스트가 자유로이 수정)
        self.gain = np.full(self.namps, float(gain))
        self.rdnoise = np.full(self.namps, float(rdnoise_adu))
        self.bias = bias_adu + 10.0 * self.rng.standard_normal(self.namps)
        self.extnames = []
        per_chip = max(1, self.namps // len(_CHIPS))
        for i in range(self.namps):
            chip = _CHIPS[min(i // per_chip, len(_CHIPS) - 1)]
            self.extnames.append("%s%02dT" % (chip, (i % per_chip) + 1))

    # -- 프레임 생성 -------------------------------------------------------
    def frame(self, name, level_adu=0.0, exptime=0.0, imagetyp=None,
              nonlin=None, pickup=None, shared_rms=0.0, persist_adu=0.0,
              adc_map=None, level_scale=None, extra_primary=None,
              flat_shape=None):
        """한 노출을 생성해 경로를 반환한다.

        level_adu    바이어스 차감 신호 기대값 [ADU] (0이면 bias 프레임)
        nonlin       f(signal_adu_array)->array — 비선형 주입 (신호 성분에만)
        pickup       (amp_rms_adu, cycles_per_row) — 행방향 사인 간섭
        shared_rms   컨트롤러별 공통모드 잡음 rms [ADU] (같은 ctrl 앰프끼리
                     동일한 픽셀열 → 상관행렬 시험용)
        persist_adu  전 앰프 데이터부에 더할 잔류 신호 [ADU] (감쇠 시험용)
        adc_map      f(uint32 code array)->array — ADC 결함 (missing code 등)
        level_scale  앰프별 배율 배열 (PRNU/경계 시험용)
        flat_shape   f(yy, xx normalized 0..1)->array — 대규모 조명 형상
        """
        ny, nx, dc = self.ny, self.nx, self.data_cols
        per_ctrl = max(1, self.namps // 2)
        shared = {c: self.rng.standard_normal((ny, nx)) * shared_rms
                  for c in (1, 2)} if shared_rms > 0 else None

        primary = fits.PrimaryHDU()
        ph = primary.header
        ph["MOCKDATA"] = True
        ph["CHIPLIST"] = ",".join(dict.fromkeys(e[0] for e in self.extnames))
        ph["EXPTIME"] = float(exptime)
        ph["IMAGETYP"] = imagetyp or ("BIAS" if level_adu <= 0 else "FLAT")
        ph["DATE-OBS"] = "2026-09-04"
        for k, v in (extra_primary or {}).items():
            ph[k] = v
        hdus = [primary]

        for i, ext in enumerate(self.extnames):
            g, rn, b = self.gain[i], self.rdnoise[i], self.bias[i]
            img = np.zeros((ny, nx))
            sig = float(level_adu) * (level_scale[i] if level_scale is not None
                                      else 1.0)
            if sig > 0:
                mean = np.full((ny, dc), sig)
                if flat_shape is not None:
                    yy, xx = np.mgrid[0:ny, 0:dc]
                    mean = mean * flat_shape(yy / ny, xx / dc)
                lam = np.clip(mean, 0, None) * g       # 기대 광전자 수
                sig_adu = self.rng.poisson(lam) / g
                if nonlin is not None:
                    sig_adu = nonlin(sig_adu)
                img[:, :dc] += sig_adu
            if persist_adu > 0:
                img[:, :dc] += persist_adu
            img += b + self.rng.standard_normal((ny, nx)) * rn
            if pickup is not None:
                amp_rms, cyc = pickup
                phase = np.arange(ny * nx).reshape(ny, nx) / nx
                img += amp_rms * np.sqrt(2) * np.sin(2 * np.pi * cyc * phase)
            if shared is not None:
                img += shared[1 if i < per_ctrl else 2]
            img[:, dc + self.ovsc_cols:] = img[:, dc - 1:dc]  # 거울 꼬리 모사

            code = np.clip(np.rint(img), 0, 65535).astype(np.uint32)
            if adc_map is not None:
                code = adc_map(code).astype(np.uint32)
            data = (code.astype(np.int32) - 32768).astype(np.int16)

            hdu = fits.ImageHDU(data=data, name=ext)
            hh = hdu.header
            hh["BZERO"], hh["BSCALE"] = 32768, 1
            hh["CHIPID"] = ext[0]
            hh["AMPID"] = i + 1
            hh["CTRLID"] = 1 if i < per_ctrl else 2
            hh["DATASEC"] = _sec(1, dc, 1, ny)
            hh["BIASSEC"] = _sec(dc + 1, dc + self.ovsc_cols, 1, ny)
            x0 = (i % per_ctrl) * dc
            hh["CCDSEC"] = _sec(x0 + 1, x0 + dc, 1, ny)
            hh["DETSEC"] = _sec(i * dc + 1, (i + 1) * dc, 1, ny)
            hh["GAIN"], hh["RDNOISE"] = float(g), float(rn * g)
            hdus.append(hdu)

        path = self.outdir / ("%s.ceu.l0amp.synth.mef.fits" % name)
        fits.HDUList(hdus).writeto(path, overwrite=True)
        return path

    # -- 편의 시퀀스 -------------------------------------------------------
    def bias_set(self, n, prefix="b", **kw):
        return [self.frame("%s%04d" % (prefix, i), 0.0, **kw)
                for i in range(n)]

    def flat_pairs(self, levels, per_level=2, rate_adu_s=2000.0, prefix="f",
                   **kw):
        """레벨별 flat (exptime = level/rate). [(level, [paths...]), ...]"""
        out, k = [], 0
        for lv in levels:
            paths = []
            for _ in range(per_level):
                paths.append(self.frame("%s%04d" % (prefix, k), lv,
                                        exptime=lv / rate_adu_s, **kw))
                k += 1
            out.append((float(lv), paths))
        return out


if __name__ == "__main__":  # 자체 검증
    import sys
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from kmt_cam_char import core

    tmp = tempfile.mkdtemp(prefix="synthl0_")
    kit = SynthL0(tmp, seed=3)
    p = kit.frame("check", level_adu=20000, exptime=10.0)
    with core.open_l0(p) as exp:
        assert len(exp.amp_names) == kit.namps, exp.amp_names
        a = core.roi_raw(exp, kit.extnames[0], roi=kit.roi)
        o = core.ovsc_raw(exp, kit.extnames[0], rows=kit.roi[0])
        # ovsc_raw는 core.OVSC_REAL 고정이라 축소 기하에선 직접 슬라이스 사용
        # (저장 int16 + BZERO=32768 -> 물리 unsigned ADU; core 헬퍼와 독립)
        o2 = np.asarray(exp.hdul[kit.extnames[0]].section[kit.roi[0], kit.ovsc],
                        dtype=np.float64) + 32768.0
        lvl = np.median(a) - np.median(o2)
        assert abs(lvl - 20000) < 200, lvl
        rn = core.mad_std(o2 - np.median(o2))
        assert 2.0 < rn < 5.5, rn
    print("OK testkit: level=%.0f ADU, ovsc RN=%.2f ADU (%s)" % (lvl, rn, p))
