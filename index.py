# ============================================================
# Free Fire Region Binder — v4 (no GetLoginData)
# Flow: Token → MajorLogin → ChooseRegion (skipped if already bound)
#       → MajorLogin (after choose)
# Every request → 200 + JSON. Never crash.
# ============================================================
import os
import json
import base64
import time
import random
import traceback
import urllib3
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

# ---- per-request budget (reset at top of _handle) ----
# Hobby default = 9s. For Vercel Pro (60s), set env FF_TIME_BUDGET="55"
TOTAL_BUDGET = float(os.environ.get("FF_TIME_BUDGET", "9"))
_MIN_CALL_BUDGET = 2.0
_REQUEST_START = time.time()  # overwritten per request


def _reset_timer():
    global _REQUEST_START
    _REQUEST_START = time.time()


def _time_left():
    try:
        return TOTAL_BUDGET - (time.time() - _REQUEST_START)
    except Exception:
        return 0.0


def _call_timeout(desired=15.0):
    """Return per-call timeout, or None only if truly out of time."""
    try:
        left = _time_left()
        if left < _MIN_CALL_BUDGET:
            return None
        return max(2.0, min(desired, left - 1.0))
    except Exception:
        return None


# ============================================================
# Home info
# ============================================================
HOME_INFO = {
    "developer": {
        "name": "DIVAN SINGH",
        "tg": "@DivanSingh",
        "channel": "https://t.me/FireXDecoding",
    },
    "endpoint": {
        "path": "/bind",
        "methods": ["GET", "POST"],
        "params": ["uid", "password", "region"],
        "optional_params": ["force"],
        "usage": {
            "GET": "/bind?uid=YOUR_UID&password=YOUR_PASSWORD&region=IND",
            "POST": {
                "url": "/bind",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "uid": "YOUR_UID",
                    "password": "YOUR_PASSWORD",
                    "region": "IND",
                },
            },
            "curl": (
                "curl -X POST 'https://YOUR_DOMAIN/bind' "
                "-H 'Content-Type: application/json' "
                "-d '{\"uid\":\"YOUR_UID\",\"password\":\"YOUR_PASSWORD\",\"region\":\"IND\"}'"
            ),
        },
    },
    "supported_regions": [
        "ME", "IND", "ID", "VN", "TH", "BD",
        "PK", "TW", "CIS", "SAC", "BR",
    ],
    "flow": [
        "1. Token grant",
        "2. MajorLogin (initial)",
        "3. ChooseRegion (target) — skipped if lock_region already == target",
        "4. MajorLogin (after choose)",
    ],
    "notes": [
        "ChooseRegion only succeeds on accounts with empty lock_region (fresh accounts).",
        "If account is already locked to a different region, rebinding fails with a clear error.",
        "If account is already on target region, ChooseRegion is skipped and flow succeeds.",
        "Set env FF_TIME_BUDGET=55 on Vercel Pro for full window; Hobby caps at 10s.",
    ],
}

DEVELOPER = HOME_INFO["developer"]

# ============================================================
# Constants
# ============================================================
aEs_KeY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
aEs_Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

cLiEnT_sEcReT = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
aPp_Id = 100067

rElEaSe_TaG = "OB55"
rUnTiMe_vErSiOn = "2.133.9"

sErVeR = "https://loginbp.ppmainecoonghj.com/"

oAuTh_ToKeN = "https://100067.connect.garena.com/oauth/guest/token/grant"

lAnGuAgE_bY_rEgIoN = {
    "ME": "ar", "IND": "hi", "ID": "id", "VN": "vi", "TH": "th",
    "BD": "bn", "PK": "ur", "TW": "zh", "CIS": "ru",
    "SAC": "es", "BR": "pt",
}

iP_aDdReSsEs = [
    "151.158.158.220", "151.158.158.221", "151.158.158.222", "151.158.158.223",
    "151.158.158.224", "151.158.158.225", "151.158.158.226", "151.158.158.227",
    "151.158.158.228", "151.158.158.229", "151.158.158.230", "151.158.158.231",
    "151.158.158.232", "151.158.158.233", "151.158.158.234", "151.158.158.235",
    "151.158.158.236", "151.158.158.237", "151.158.158.238", "151.158.158.239",
]

mSdK_aGeNtS = [
    "GarenaMSDK/4.0.42(KB2003 ;Android 13;en;HK;app 2.130.1 2019118332;)",
    "GarenaMSDK/4.0.42(SM-G998B ;Android 14;en;IN;app 2.131.0 2019118527;)",
    "GarenaMSDK/4.0.42(Pixel 6 ;Android 14;en;US;app 2.131.1 2019118602;)",
]

uNiTy_AgEnTs = [
    "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
    "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
]

MAX_BODY_BYTES = 8192
MAX_UID_LEN = 64
MAX_PWD_LEN = 256
MAX_REGION_LEN = 8


# ============================================================
# Safe helpers
# ============================================================
def safe_choice(seq, default=None):
    try:
        return random.choice(seq)
    except Exception:
        return default


def safe_json(obj, **kw):
    try:
        return json.dumps(obj, ensure_ascii=False, default=str, **kw)
    except Exception:
        try:
            return json.dumps(obj, ensure_ascii=True, default=str, **kw)
        except Exception:
            try:
                return json.dumps({"success": False, "error": "serialization_failed"})
            except Exception:
                return '{"success":false}'


# ============================================================
# Protobuf helpers
# ============================================================
def wRiTe_vArInT(vAlUe):
    oUt = []
    vAlUe = int(vAlUe)
    while vAlUe > 127:
        oUt.append((vAlUe & 0x7F) | 0x80)
        vAlUe >>= 7
    oUt.append(vAlUe)
    return bytes(oUt)


def fIeLd_iNt(n, v):
    return wRiTe_vArInT((n << 3) | 0) + wRiTe_vArInT(v)


def fIeLd_sTr(n, v):
    e = str(v).encode("utf-8")
    return wRiTe_vArInT((n << 3) | 2) + wRiTe_vArInT(len(e)) + e


def fIeLd_bYtEs(n, v):
    v = bytes(v)
    return wRiTe_vArInT((n << 3) | 2) + wRiTe_vArInT(len(v)) + v


def aSsEmBlE_pRoTo(fields):
    buf = bytearray()
    for k, v in fields.items():
        try:
            if isinstance(v, bool):
                buf.extend(fIeLd_iNt(k, int(v)))
            elif isinstance(v, int):
                buf.extend(fIeLd_iNt(k, v))
            elif isinstance(v, str):
                buf.extend(fIeLd_sTr(k, v))
            elif isinstance(v, (bytes, bytearray)):
                buf.extend(fIeLd_bYtEs(k, bytes(v)))
        except Exception:
            continue
    return bytes(buf)


def rEaD_vArInT(d, o):
    r, s = 0, 0
    while True:
        if o >= len(d):
            raise IndexError("eof")
        b = d[o]
        r |= (b & 0x7F) << s
        o += 1
        if not (b & 0x80):
            break
        s += 7
        if s > 63:
            raise ValueError("varint too long")
    return r, o


def pArSe_pRoTo(d):
    out, o = {}, 0
    if not d:
        return out
    while o < len(d):
        try:
            tag, o = rEaD_vArInT(d, o)
        except Exception:
            break
        fn, wt = tag >> 3, tag & 0x7
        if fn <= 0:
            break
        try:
            if wt == 0:
                v, o = rEaD_vArInT(d, o)
                out[fn] = v
            elif wt == 2:
                ln, o = rEaD_vArInT(d, o)
                if o + ln > len(d):
                    break
                chunk = d[o:o + ln]
                o += ln
                try:
                    out[fn] = chunk.decode("utf-8")
                except Exception:
                    out[fn] = chunk.hex()
            elif wt == 1:
                out[fn] = d[o:o + 8].hex()
                o += 8
            elif wt == 5:
                out[fn] = d[o:o + 4].hex()
                o += 4
            else:
                break
        except Exception:
            break
    return out


def eNcRyPt_aEs(plain):
    return AES.new(aEs_KeY, AES.MODE_CBC, aEs_Iv).encrypt(pad(plain, AES.block_size))


def dEcOdE_jWt(tok):
    try:
        if not tok or not isinstance(tok, str):
            return {}
        p = tok.split(".")
        if len(p) < 2:
            return {}
        payload = p[1] + "=" * ((4 - len(p[1]) % 4) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except Exception:
        return {}


def jWt_ReGiOn(tok):
    try:
        d = dEcOdE_jWt(tok)
        return d.get("lock_region") or d.get("noti_region")
    except Exception:
        return None


def gA_sV():
    try:
        return str(int(time.time()))
    except Exception:
        return "0"


# ============================================================
# Network calls
# ============================================================
def request_token(session, uid, password, user_agent):
    to = _call_timeout(20.0)
    if to is None:
        raise Exception("time_budget_exhausted_token")
    payload = {
        "uid": uid, "password": password,
        "response_type": "token", "client_type": "2",
        "client_secret": cLiEnT_sEcReT, "client_id": "100067",
    }
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
    }
    r = session.post(oAuTh_ToKeN, data=payload, headers=headers, timeout=to)
    if r.status_code != 200:
        raise Exception(f"Token HTTP {r.status_code}: {r.text[:200]}")
    try:
        data = r.json()
    except Exception:
        raise Exception(f"Token JSON parse failed: {r.text[:200]}")
    if not isinstance(data, dict):
        raise Exception(f"Token unexpected shape: {str(data)[:200]}")
    at, oid = data.get("access_token"), data.get("open_id")
    if not at or not oid:
        raise Exception(f"Token grant failed: {str(data)[:200]}")
    return str(at), str(oid)


def major_login_body(access_token, open_id, platform_type, region, ip):
    region_s = str(region).upper()
    return {
        3: time.strftime("%Y-%m-%d %H:%M:%S"),
        4: "free fire", 5: 1, 7: rUnTiMe_vErSiOn,
        8: "Android OS 10 / API-29 (QP1A.190711.020/1617006012)",
        9: "Handheld", 10: "Vi India", 11: "WIFI",
        12: 1600, 13: 720, 14: "320",
        15: "ARM64 FP ASIMD AES | 2301 | 8", 16: 2799,
        17: "PowerVR Rogue GE8320",
        18: "OpenGL ES 3.2 build 1.11@5425693",
        19: "Google|9f7d6b8b-b10c-454a-852d-06332cd498eb",
        20: ip, 21: lAnGuAgE_bY_rEgIoN.get(region_s, "en"),
        22: open_id, 23: str(platform_type),
        24: "Handheld", 25: "realme RMX2189", 26: region_s,
        29: access_token, 30: 1,
        41: "Vi India", 42: "WIFI",
        57: "1ac4b80ecf0478a44203bf8fac6120f5",
        60: 19799, 61: 2536, 62: 5056, 64: 2768,
        65: 19999, 66: 2536, 67: 19799,
        73: 1,
        74: "/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/lib/arm64",
        76: 2,
        77: "38f4751a330688ab124c2c804cec90a5|/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/base.apk",
        78: 2, 79: 2, 81: "64", 83: "2019118527",
        86: "OpenGLES3", 87: 3071, 88: 4,
        92: 67920, 93: "android_max",
        94: "KqsHT+UrR1HKqb6+1db+Ofei+NtZr2+hbiBo3yKDL8w+8E3S5qF2IgEEe1fFQFyHRzl4iyHjHp+QsfeLbjJ6+DidTiKxm0ak2uYYa6QR4nAUdlZR",
        95: 111107,
        96: '{"cur_rate":null,"support_etc2":true}',
        97: 1, 98: 1, 99: "4", 100: "4", 102: "",
        104: 83812, 105: 1,
        106: "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a",
        107: "1.9393e7b8e53e8aeb",
    }


def send_major_login(session, access_token, open_id, platform_type=4, user_agent=None, region="IND"):
    to = _call_timeout(20.0)
    if to is None:
        raise Exception("time_budget_exhausted_major_login")
    url = sErVeR + "MajorLogin"
    host = url.split("/")[2] if "//" in url else url
    body = major_login_body(access_token, open_id, platform_type, region,
                            safe_choice(iP_aDdReSsEs, "151.158.158.220"))
    enc = eNcRyPt_aEs(aSsEmBlE_pRoTo(body))
    headers = {
        "Host": host,
        "User-Agent": user_agent or uNiTy_AgEnTs[0],
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": gA_sV(),
        "Authorization": "Bearer",
        "X-GA": "v1 1",
        "ReleaseVersion": rElEaSe_TaG,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(enc)),
    }
    r = session.post(url, data=enc, headers=headers, timeout=to, verify=False)
    if r.status_code != 200:
        raise Exception(f"MajorLogin HTTP {r.status_code}: {r.text[:200]}")
    if len(r.content) <= 64:
        raise Exception("MajorLogin response too short")
    return pArSe_pRoTo(r.content[64:])


def send_choose_region(session, region, jwt, user_agent=None):
    to = _call_timeout(15.0)
    if to is None:
        raise Exception("time_budget_exhausted_choose_region")
    url = sErVeR + "ChooseRegion"
    host = url.split("/")[2] if "//" in url else url
    target = "RU" if str(region).upper() == "CIS" else str(region).upper()
    enc = eNcRyPt_aEs(aSsEmBlE_pRoTo({1: target}))
    headers = {
        "Host": host,
        "User-Agent": user_agent or uNiTy_AgEnTs[0],
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": gA_sV(),
        "Authorization": f"Bearer {jwt}",
        "X-GA": "v1 1",
        "ReleaseVersion": rElEaSe_TaG,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(enc)),
    }
    return session.post(url, data=enc, headers=headers, timeout=to, verify=False)


# ============================================================
# Main flow — 4 steps, no GetLoginData
# ============================================================
def bind_region(uid, password, region, force=False):
    region = str(region).upper()
    session = None
    try:
        session = requests.Session()
        try:
            session.verify = False
        except Exception:
            pass

        mSDK_ua = safe_choice(mSdK_aGeNtS, mSdK_aGeNtS[0])
        unity_ua = safe_choice(uNiTy_AgEnTs, uNiTy_AgEnTs[0])

        # ── STEP 1: Token grant ──────────────────────────────
        try:
            access_token, open_id = request_token(session, uid, password, mSDK_ua)
        except Exception as e:
            return {"success": False,
                    "error": f"token_grant_failed: {e}",
                    "stage": "token",
                    "developer": DEVELOPER}

        # ── STEP 2: Initial MajorLogin ───────────────────────
        try:
            login1 = send_major_login(session, access_token, open_id, 4, unity_ua, region)
        except Exception as e:
            return {"success": False,
                    "error": f"major_login_initial_failed: {e}",
                    "stage": "major_login_initial",
                    "developer": DEVELOPER}

        jwt1 = login1.get(8)
        if isinstance(jwt1, bytes):
            try:
                jwt1 = jwt1.decode("utf-8", errors="ignore")
            except Exception:
                jwt1 = ""
        if not jwt1:
            return {"success": False,
                    "error": "major_login_initial_no_jwt",
                    "stage": "major_login_initial",
                    "developer": DEVELOPER}

        target = "RU" if region == "CIS" else region
        previous_region = jWt_ReGiOn(jwt1)
        already_on_target = bool(previous_region) and str(previous_region).upper() == target

        # ── STEP 3: ChooseRegion (skipped if already on target) ─
        choose_region_status = None
        choose_region_body = None
        choose_region_ok = False
        choose_region_skipped = False

        if already_on_target and not force:
            choose_region_skipped = True
        else:
            try:
                cr = send_choose_region(session, region, jwt1, unity_ua)
                choose_region_status = getattr(cr, "status_code", 0)
                try:
                    choose_region_body = (cr.text or "")[:1000] if hasattr(cr, "text") else None
                except Exception:
                    choose_region_body = None
                if choose_region_status == 200:
                    choose_region_ok = True
            except Exception as e:
                choose_region_status = None
                choose_region_body = str(e)[:500]

        # Failure handling — not on target and ChooseRegion rejected → can't rebind
        if not choose_region_ok and not choose_region_skipped and not already_on_target:
            return {
                "success": False,
                "error": f"choose_region_failed_status_{choose_region_status}",
                "stage": "choose_region",
                "target_region": target,
                "previous_region": previous_region,
                "choose_region_status": choose_region_status,
                "choose_region_body": choose_region_body,
                "note": (
                    "ChooseRegion is a one-time endpoint — it only works on "
                    "accounts whose lock_region is empty (fresh / never played). "
                    f"This account is already locked to {previous_region!r} and "
                    f"cannot be rebound to {target!r}. Use a fresh account or "
                    "the force=true param to inspect the raw server response."
                ),
                "jwt": jwt1,
                "developer": DEVELOPER,
            }

        # ── STEP 4: MajorLogin (after choose, target region) ──
        try:
            login2 = send_major_login(session, access_token, open_id, 4, unity_ua, region)
        except Exception as e:
            return {"success": False,
                    "error": f"major_login_after_choose_failed: {e}",
                    "stage": "major_login_after_choose",
                    "previous_region": previous_region,
                    "choose_region_status": choose_region_status,
                    "developer": DEVELOPER}

        jwt2 = login2.get(8)
        if isinstance(jwt2, bytes):
            try:
                jwt2 = jwt2.decode("utf-8", errors="ignore")
            except Exception:
                jwt2 = ""
        if not jwt2:
            return {"success": False,
                    "error": "major_login_after_choose_no_jwt",
                    "stage": "major_login_after_choose",
                    "previous_region": previous_region,
                    "developer": DEVELOPER}

        new_lock = jWt_ReGiOn(jwt2)
        ok = bool(new_lock) and str(new_lock).upper() == target

        if ok and choose_region_ok:
            message = f"Region bound to {target}"
        elif ok and choose_region_skipped:
            message = f"Account already on {target} (ChooseRegion skipped)"
        elif ok and already_on_target:
            message = f"Account already on {target} (ChooseRegion failed but region matches)"
        else:
            message = f"lock_region={new_lock!r} (expected {target})"

        return {
            "success":               ok,
            "message":               message,
            "target_region":         target,
            "previous_region":       previous_region,
            "new_lock_region":       new_lock,
            "changed":               choose_region_ok,
            "already_bound":         choose_region_skipped or already_on_target,
            "choose_region_status":  choose_region_status,
            "choose_region_body":    choose_region_body if not choose_region_ok else None,
            "uid":                   uid,
            "jwt":                   jwt2,
            "developer":             DEVELOPER,
        }

    except BaseException as e:
        return {"success": False,
                "error": f"unexpected_exception: {type(e).__name__}: {e}",
                "stage": "top_level",
                "developer": DEVELOPER}
    finally:
        try:
            if session is not None:
                session.close()
        except BaseException:
            pass


# ============================================================
# HTTP handler
# ============================================================
class handler(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass

    def _send(self, status, body_str):
        try:
            if getattr(self, "_sent", False):
                return
            self._sent = True
        except BaseException:
            return
        try:
            data = body_str.encode("utf-8") if isinstance(body_str, str) else b""
        except BaseException:
            data = b'{"success":false,"error":"encoding_failed"}'
        try:
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods",
                             "GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
        except BaseException:
            return
        try:
            if self.command != "HEAD":
                self.wfile.write(data)
        except BaseException:
            pass

    def _safe_handle(self):
        try:
            self._handle()
        except BaseException as e:
            try:
                self._send(200, safe_json({
                    "success": False,
                    "error": f"handler_exception: {type(e).__name__}: {e}",
                    "developer": DEVELOPER,
                }))
            except BaseException:
                pass

    def do_GET(self):     self._safe_handle()
    def do_POST(self):    self._safe_handle()
    def do_PUT(self):     self._safe_handle()
    def do_DELETE(self):  self._safe_handle()
    def do_PATCH(self):   self._safe_handle()
    def do_HEAD(self):    self._safe_handle()
    def do_TRACE(self):   self._safe_handle()

    def do_OPTIONS(self):
        try:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods",
                             "GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", "0")
            self.end_headers()
        except BaseException:
            pass

    def _read_body(self):
        try:
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
            except BaseException:
                length = 0
            if length <= 0:
                return ""
            raw = self.rfile.read(min(length, MAX_BODY_BYTES))
            try:
                return raw.decode("utf-8", errors="ignore")
            except BaseException:
                return ""
        except BaseException:
            return ""

    def _handle(self):
        # ⚡ reset per-request timer
        _reset_timer()

        # ---- 1) parse URL ----
        raw_path = "/"
        params = {}
        try:
            parsed = urlparse(self.path or "/")
            raw_path = parsed.path or "/"
            params = {k: v[0] for k, v in parse_qs(parsed.query or "").items()}
        except BaseException:
            raw_path, params = "/", {}

        # ---- 2) merge POST body ----
        if self.command in ("POST", "PUT", "PATCH"):
            raw_s = self._read_body()
            if raw_s.strip():
                try:
                    pj = json.loads(raw_s)
                    if isinstance(pj, dict):
                        params.update(pj)
                except BaseException:
                    try:
                        params.update({k: v[0] for k, v in parse_qs(raw_s).items()})
                    except BaseException:
                        pass

        # ---- 3) normalize inputs ----
        try:
            uid = str(params.get("uid", "") or "").strip()
            password = str(params.get("password", "") or "").strip()
            region = str(params.get("region", "") or "").strip().upper()
        except BaseException:
            uid, password, region = "", "", ""

        if len(uid) > MAX_UID_LEN:       uid = uid[:MAX_UID_LEN]
        if len(password) > MAX_PWD_LEN:  password = password[:MAX_PWD_LEN]
        if len(region) > MAX_REGION_LEN: region = region[:MAX_REGION_LEN]

        force = str(params.get("force", "") or "").strip().lower() in ("1", "true", "yes")

        # ---- 4) recover intended path (Vercel rewrites → /index.py) ----
        path = raw_path.rstrip("/") or "/"

        explicit = str(params.pop("__path", "") or "").strip()
        if explicit:
            if not explicit.startswith("/"):
                explicit = "/" + explicit
            path = explicit.rstrip("/") or "/"
        elif path in ("/index.py", "/index", "/api", "/api/index", "/api/index.py"):
            if uid or password or region:
                path = "/bind"
            else:
                path = "/"

        # ---- 5) route ----
        if path == "/bind":
            missing = []
            if not uid:       missing.append("uid")
            if not password:  missing.append("password")
            if not region:    missing.append("region")

            if missing:
                self._send(200, safe_json({
                    "success": False,
                    "error": "missing_parameters",
                    "missing": missing,
                    "required": ["uid", "password", "region"],
                    "developer": DEVELOPER,
                }))
                return

            if region not in lAnGuAgE_bY_rEgIoN:
                self._send(200, safe_json({
                    "success": False,
                    "error": "invalid_region",
                    "given": region,
                    "supported_regions": sorted(lAnGuAgE_bY_rEgIoN.keys()),
                    "developer": DEVELOPER,
                }))
                return

            try:
                result = bind_region(uid, password, region, force=force)
            except BaseException as e:
                result = {"success": False,
                          "error": f"bind_region_exception: {type(e).__name__}: {e}",
                          "developer": DEVELOPER}

            if not isinstance(result, dict):
                result = {"success": False,
                          "error": "invalid_result_shape",
                          "developer": DEVELOPER}

            result.setdefault("developer", DEVELOPER)
            self._send(200, safe_json(result))
            return

        if path == "/":
            self._send(200, safe_json(HOME_INFO, indent=2))
            return

        self._send(200, safe_json({
            "success": False,
            "error": "unknown_endpoint",
            "given": raw_path,
            "valid_endpoints": {"home": "/", "bind": "/bind"},
            "developer": DEVELOPER,
        }))
