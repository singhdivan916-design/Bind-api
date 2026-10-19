# ============================================================
# Bulletproof Free Fire Region Binder — v2 (per-request timer)
# Every request → 200 + JSON. Never crash. Never preemptively skip.
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

# ---- per-request budget (reset in _handle) ----
# Hobby-safe default = 9s. For Vercel Pro (60s maxDuration), set env:
#   FF_TIME_BUDGET = "55"
TOTAL_BUDGET = float(os.environ.get("FF_TIME_BUDGET", "9"))
_MIN_CALL_BUDGET = 2.0
_REQUEST_START = time.time()   # overwritten per request

def _reset_timer():
    global _REQUEST_START
    _REQUEST_START = time.time()

def _time_left():
    try:
        return TOTAL_BUDGET - (time.time() - _REQUEST_START)
    except Exception:
        return 0.0

def _call_timeout(desired=15.0):
    """Return per-call timeout, or None only if truly no time left."""
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
    "notes": [
        "Total flow needs ~7-12s. Vercel Hobby caps at 10s — use Pro (60s) for reliability.",
        "On Pro set env FF_TIME_BUDGET=55 for the full window.",
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
cLiEnT_IND = "https://client.ind.freefiremobile.com/"
cLiEnT_US = "https://client.us.freefiremobile.com/"
cLiEnT_GLOBAL = "https://clientbp.ppmainecoonghj.com/"

oAuTh_ToKeN = "https://100067.connect.garena.com/oauth/guest/token/grant"

lAnGuAgE_bY_rEgIoN = {
    "ME": "ar", "IND": "hi", "ID": "id", "VN": "vi", "TH": "th",
    "BD": "bn", "PK": "ur", "TW": "zh", "CIS": "ru",
    "SAC": "es", "BR": "pt",
}
aMeRiCaN_rEgIoNs = {"BR", "SAC"}

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
                out[fn] = d[o:o + 8].hex(); o += 8
            elif wt == 5:
                out[fn] = d[o:o + 4].hex(); o += 4
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

def server_endpoint(_region):
    return sErVeR

def client_endpoint(region):
    try:
        c = str(region).upper()
    except Exception:
        return cLiEnT_GLOBAL
    if c == "IND":
        return cLiEnT_IND
    if c in aMeRiCaN_rEgIoNs:
        return cLiEnT_US
    return cLiEnT_GLOBAL

# ============================================================
# Network calls — generous timeouts, only skip if truly out of time
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
    url = server_endpoint(region) + "MajorLogin"
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
    url = server_endpoint(region) + "ChooseRegion"
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

def send_get_login_data(session, jwt, open_id, region, user_agent):
    to = _call_timeout(8.0)
    if to is None:
        return 0, b""
    url = client_endpoint(region) + "GetLoginData"
    host = url.split("/")[2] if "//" in url else url
    body = major_login_body(jwt, open_id, 4, region,
                            safe_choice(iP_aDdReSsEs, "151.158.158.220"))
    enc = eNcRyPt_aEs(aSsEmBlE_pRoTo(body))
    headers = {
        "Host": host,
        "User-Agent": user_agent or uNiTy_AgEnTs[1],
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "Authorization": f"Bearer {jwt}",
        "X-GA": "v1 1",
        "ReleaseVersion": rElEaSe_TaG,
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2022.3.47f1",
    }
    r = session.post(url, headers=headers, data=enc, verify=False, timeout=to)
    return r.status_code, r.content

# ============================================================
# Main flow
# ============================================================
def bind_region(uid, password, region):
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

        # 1) token — required, never skipped
        try:
            access_token, open_id = request_token(session, uid, password, mSDK_ua)
        except Exception as e:
            return {"success": False, "error": f"token_grant_failed: {e}",
                    "stage": "token", "developer": DEVELOPER}

        # 2) initial MajorLogin — required
        try:
            login1 = send_major_login(session, access_token, open_id, 4, unity_ua, region)
        except Exception as e:
            return {"success": False, "error": f"major_login_failed: {e}",
                    "stage": "major_login", "developer": DEVELOPER}

        jwt = login1.get(8)
        if isinstance(jwt, bytes):
            try:
                jwt = jwt.decode("utf-8", errors="ignore")
            except Exception:
                jwt = ""
        if not jwt:
            return {"success": False, "error": "major_login_no_jwt",
                    "stage": "major_login", "developer": DEVELOPER}

        target = "RU" if region == "CIS" else region
        current_lock = jWt_ReGiOn(jwt)

        if current_lock and str(current_lock).upper() == target:
            return {"success": True,
                    "message": f"Account already bound to {target}",
                    "region": region, "lock_region": current_lock,
                    "uid": uid, "jwt": jwt, "developer": DEVELOPER}

        # 3) ChooseRegion — required
        try:
            cr = send_choose_region(session, region, jwt, unity_ua)
            if getattr(cr, "status_code", 0) != 200:
                return {"success": False,
                        "error": f"choose_region_http_{getattr(cr, 'status_code', 0)}",
                        "stage": "choose_region",
                        "previous_region": current_lock,
                        "jwt": jwt, "developer": DEVELOPER}
        except Exception as e:
            return {"success": False,
                    "error": f"choose_region_exception: {e}",
                    "stage": "choose_region",
                    "previous_region": current_lock,
                    "jwt": jwt, "developer": DEVELOPER}

        # 4) re-login — required
        new_jwt = None
        relogin_err = None
        try:
            login2 = send_major_login(session, access_token, open_id, 4, unity_ua, region)
            nj = login2.get(8)
            if isinstance(nj, bytes):
                nj = nj.decode("utf-8", errors="ignore")
            if nj:
                new_jwt = nj
        except Exception as e:
            relogin_err = str(e)

        if not new_jwt:
            return {"success": False,
                    "error": ("relogin_no_jwt_after_choose_region"
                              + (f": {relogin_err}" if relogin_err else "")),
                    "stage": "relogin",
                    "previous_region": current_lock,
                    "developer": DEVELOPER}

        new_lock = jWt_ReGiOn(new_jwt)

        # 5) optional verification — skipped only if out of time
        verified = None
        try:
            st, content = send_get_login_data(session, new_jwt, open_id, region, unity_ua)
            if st == 200:
                parsed = pArSe_pRoTo(content)
                verified = {"account_uid": parsed.get(1),
                            "account_name": parsed.get(4),
                            "region": parsed.get(3)}
        except Exception:
            verified = None

        ok = bool(new_lock) and str(new_lock).upper() == target
        return {
            "success": ok,
            "message": (f"Region bound to {target}" if ok
                        else f"lock_region={new_lock!r} (expected {target})"),
            "target_region": target,
            "previous_region": current_lock,
            "new_lock_region": new_lock,
            "uid": uid,
            "jwt": new_jwt,
            "login_data": verified,
            "developer": DEVELOPER,
        }

    except BaseException as e:
        return {"success": False,
                "error": f"unexpected_exception: {type(e).__name__}: {e}",
                "stage": "top_level", "developer": DEVELOPER}
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
        # ⚡ KEY FIX: reset the timer on every request
        _reset_timer()

        path = "/"
        params = {}
        try:
            parsed = urlparse(self.path or "/")
            path = (parsed.path or "/").rstrip("/") or "/"
            params = {k: v[0] for k, v in parse_qs(parsed.query or "").items()}
        except BaseException:
            path, params = "/", {}

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

        try:
            uid = str(params.get("uid", "") or "").strip()
            password = str(params.get("password", "") or "").strip()
            region = str(params.get("region", "") or "").strip().upper()
        except BaseException:
            uid, password, region = "", "", ""

        if len(uid) > MAX_UID_LEN:      uid = uid[:MAX_UID_LEN]
        if len(password) > MAX_PWD_LEN: password = password[:MAX_PWD_LEN]
        if len(region) > MAX_REGION_LEN: region = region[:MAX_REGION_LEN]

        # ---- /bind ----
        if path == "/bind":
            missing = []
            if not uid:      missing.append("uid")
            if not password: missing.append("password")
            if not region:   missing.append("region")
            if missing:
                self._send(200, safe_json({
                    "success": False, "error": "missing_parameters",
                    "missing": missing,
                    "required": ["uid", "password", "region"],
                    "developer": DEVELOPER,
                }))
                return

            if region not in lAnGuAgE_bY_rEgIoN:
                self._send(200, safe_json({
                    "success": False, "error": "invalid_region",
                    "given": region,
                    "supported_regions": sorted(lAnGuAgE_bY_rEgIoN.keys()),
                    "developer": DEVELOPER,
                }))
                return

            try:
                result = bind_region(uid, password, region)
            except BaseException as e:
                result = {"success": False,
                          "error": f"bind_region_exception: {type(e).__name__}: {e}",
                          "developer": DEVELOPER}

            if not isinstance(result, dict):
                result = {"success": False, "error": "invalid_result_shape",
                          "developer": DEVELOPER}

            result.setdefault("developer", DEVELOPER)
            self._send(200, safe_json(result))
            return

        # ---- / (home) ----
        if path == "/":
            self._send(200, safe_json(HOME_INFO, indent=2))
            return

        self._send(200, safe_json({
            "success": False, "error": "unknown_endpoint", "given": path,
            "valid_endpoints": {"home": "/", "bind": "/bind"},
            "developer": DEVELOPER,
        }))
