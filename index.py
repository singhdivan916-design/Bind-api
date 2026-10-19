# ============================================================
# Free Fire Region Binder
# ============================================================
import os
import json
import base64
import time
import random
import urllib3
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

TOTAL_BUDGET = float(os.environ.get("FF_TIME_BUDGET", "9"))
_MIN_CALL_BUDGET = 2.0
_REQUEST_START = time.time()


def _reset_timer():
    global _REQUEST_START
    _REQUEST_START = time.time()


def _time_left():
    try:
        return TOTAL_BUDGET - (time.time() - _REQUEST_START)
    except Exception:
        return 0.0


def _call_timeout(desired=15.0):
    try:
        left = _time_left()
        if left < _MIN_CALL_BUDGET:
            return None
        return max(2.0, min(desired, left - 1.0))
    except Exception:
        return None


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
}

DEVELOPER = HOME_INFO["developer"]

aEs_KeY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
aEs_Iv  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

cLiEnT_sEcReT = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
aPp_Id = 100067

rElEaSe_TaG     = "OB55"
rUnTiMe_vErSiOn = "1.132.11"

sErVeR = "https://loginbp.ppmainecoonghj.com/"
oAuTh_ToKeN = "https://100067.connect.garena.com/oauth/guest/token/grant"

cLiEnT_IND    = "https://client.ind.freefiremobile.com/"
cLiEnT_US     = "https://client.us.freefiremobile.com/"
cLiEnT_GLOBAL = "https://clientbp.ppmainecoonghj.com/"

lAnGuAgE_bY_rEgIoN = {
    "ME": "ar", "IND": "hi", "ID": "id", "VN": "vi", "TH": "th",
    "BD": "bn", "PK": "ur", "TW": "zh", "CIS": "ru",
    "SAC": "es", "BR": "pt-br",
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
            return '{"success":false}'


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


def region_language(region):
    try:
        r = str(region).upper()
    except Exception:
        return "en"
    return lAnGuAgE_bY_rEgIoN.get(r, "en")


def _extract_field_str(raw, field_no):
    if not raw:
        return None
    try:
        pos, n = 0, len(raw)

        def read_varint(buf, p):
            res, sh = 0, 0
            while p < len(buf) and sh < 64:
                b = buf[p]
                p += 1
                res |= (b & 0x7F) << sh
                if not (b & 0x80):
                    return res, p
                sh += 7
            raise ValueError("bad_varint")

        while pos < n:
            key, pos = read_varint(raw, pos)
            fn = key >> 3
            wt = key & 0x07
            if fn == 0:
                return None
            if wt == 0:
                _, pos = read_varint(raw, pos)
            elif wt == 2:
                ln, pos = read_varint(raw, pos)
                if pos + ln > n:
                    return None
                val = raw[pos:pos + ln]
                pos += ln
                if fn == field_no:
                    try:
                        return val.decode("utf-8")
                    except Exception:
                        return None
            elif wt == 5:
                pos += 4
                if pos > n:
                    return None
            elif wt == 1:
                pos += 8
                if pos > n:
                    return None
            else:
                return None
        return None
    except Exception:
        return None


def _find_proto_offset(content):
    if not content:
        return 0
    for off in range(0, min(120, len(content))):
        fa = _extract_field_str(content[off:], 14)
        if fa and ":" in fa:
            return off
    return 0


def major_login_body(access_token, open_id, platform_type, region, ip):
    language = region_language(region)
    memory_available_inner = fIeLd_iNt(6, 55) + fIeLd_iNt(8, 81)

    return {
        3: time.strftime("%Y-%m-%d %H:%M:%S"),
        4: "free fire",
        5: 1,
        7: rUnTiMe_vErSiOn,
        8: "Android OS 15 / API-35 (AP3A.240905.015.A2/185014)",
        9: "Handheld",
        10: "TUNTEL",
        11: "WIFI",
        12: 1600,
        13: 719,
        14: "234",
        15: "ARM64 FP ASIMD AES | 1820 | 8",
        16: 2798,
        17: "Mali-G57",
        18: "OpenGL ES 3.2 v1.r49p1-04eac0.2848c17a2fd4e9340e06555168eaa3c9",
        19: "Google|f744e396-5694-4e65-995d-97a958f2bd1f",
        20: ip,
        21: language,
        22: open_id,
        23: "4",
        24: "Handheld",
        25: memory_available_inner,
        29: access_token,
        30: 1,
        41: "TUNTEL",
        42: "WIFI",
        57: "7428b253defc164018c604a1ebbfebdf",
        60: 49973,
        61: 11338,
        62: 854,
        63: 11466,
        64: 11466,
        65: 49973,
        66: 11466,
        67: 49973,
        73: 2,
        74: "/data/app/~~lHFxTCCbupG2QVJmsURtZw==/com.dts.freefireth-N3aCHpHNXpdxjD80uIIbww==/lib/arm64",
        76: 1,
        77: "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~lHFxTCCbupG2QVJmsURtZw==/com.dts.freefireth-N3aCHpHNXpdxjD80uIIbww==/base.apk",
        78: 3,
        79: 2,
        81: "64",
        83: "2019121229",
        86: "OpenGLES2",
        87: 8191,
        88: 4,
        92: 15078,
        93: "android",
        94: "KqsHTx3+QOmBRR1WKvaWewlcpqJBfjki+PPHQoQG8+0yV+Uos7gUFFjHMQ/e7u6han6Fl77r7c3vMN3p8UbKgN+nfycQCgwBmWgBzomx2gj84c+p",
        95: 111207,
        96: '{"cur_rate":[90,60,120],"support_etc2":false}',
        97: 1,
        98: 0,
        99: "4",
        100: "4",
        102: b"\x17]ENWU\x0eR5",
        104: 52882,
        105: 1,
        106: "https://dl.ak.freefiremobile.com/live/ABHotUpdates/|https://core-ak.freefiremobile.com/live/ABHotUpdates/|6b2078db9d22dd98f8e9386a39af8462",
        107: "c8e41b7a93f02d56e1a94c7b8203f5d1",
    }


def request_token(session, uid, password, user_agent):
    to = _call_timeout(20.0)
    if to is None:
        raise Exception("timeout")
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
        raise Exception(f"http_{r.status_code}")
    try:
        data = r.json()
    except Exception:
        raise Exception("bad_response")
    if not isinstance(data, dict):
        raise Exception("bad_response")
    at, oid = data.get("access_token"), data.get("open_id")
    if not at or not oid:
        raise Exception("auth_rejected")
    return str(at), str(oid)


def send_major_login(session, access_token, open_id, platform_type=4, user_agent=None, region="IND"):
    to = _call_timeout(20.0)
    if to is None:
        raise Exception("timeout")
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
        raise Exception(f"http_{r.status_code}")
    if len(r.content) <= 64:
        raise Exception("bad_response")
    return pArSe_pRoTo(r.content[64:])


def send_choose_region(session, region, jwt, user_agent=None):
    to = _call_timeout(15.0)
    if to is None:
        raise Exception("timeout")
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


def send_get_login_data(session, base_url, jwt, body_payload, user_agent=None):
    to = _call_timeout(15.0)
    if to is None:
        raise Exception("timeout")

    url = base_url.rstrip("/") + "/GetLoginData"
    host = url.split("/")[2] if "//" in url else url

    headers = {
        "Host": host,
        "User-Agent": user_agent or "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept-Encoding": "gzip",
        "Expect": "100-continue",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "X-GA-SV": "1789535859",
        "X-GA": "v1 1",
        "ReleaseVersion": rElEaSe_TaG,
        "Authorization": f"Bearer {jwt}",
    }

    r = session.post(url, data=body_payload, headers=headers, timeout=to, verify=False)
    if r.status_code != 200:
        raise Exception(f"http_{r.status_code}")

    content = r.content
    if not content:
        raise Exception("empty_response")

    offset = _find_proto_offset(content)
    blob = content[offset:] if offset else content

    fa = _extract_field_str(blob, 14)
    ia = _extract_field_str(blob, 32)

    if not fa or not ia:
        for off in range(0, min(120, len(content))):
            f = _extract_field_str(content[off:], 14)
            i = _extract_field_str(content[off:], 32)
            if f and ":" in f and i and ":" in i:
                fa, ia = f, i
                break

    parsed = pArSe_pRoTo(blob)

    return {
        "functional_addrs":    fa or parsed.get(14),
        "informational_addrs": ia or parsed.get(32),
        "account_uid":         parsed.get(1),
        "region":              parsed.get(3),
        "nickname":            parsed.get(4),
    }


def _execute(uid, password, region, force=False):
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

        try:
            access_token, open_id = request_token(session, uid, password, mSDK_ua)
        except Exception:
            return {"success": False, "error": "auth_failed", "developer": DEVELOPER}

        try:
            login1 = send_major_login(session, access_token, open_id, 4, unity_ua, region)
        except Exception:
            return {"success": False, "error": "login_failed", "developer": DEVELOPER}

        jwt1 = login1.get(8)
        if isinstance(jwt1, bytes):
            try:
                jwt1 = jwt1.decode("utf-8", errors="ignore")
            except Exception:
                jwt1 = ""
        if not jwt1:
            return {"success": False, "error": "login_failed", "developer": DEVELOPER}

        target = "RU" if region == "CIS" else region
        previous_region = jWt_ReGiOn(jwt1)
        already_on_target = bool(previous_region) and str(previous_region).upper() == target

        choose_ok = False
        choose_skipped = False

        if already_on_target and not force:
            choose_skipped = True
        else:
            try:
                cr = send_choose_region(session, region, jwt1, unity_ua)
                if getattr(cr, "status_code", 0) == 200:
                    choose_ok = True
            except Exception:
                pass

        if not choose_ok and not choose_skipped and not already_on_target:
            return {"success": False, "error": "region_bind_rejected", "developer": DEVELOPER}

        try:
            login2 = send_major_login(session, access_token, open_id, 4, unity_ua, region)
        except Exception:
            return {"success": False, "error": "login_failed", "developer": DEVELOPER}

        jwt2 = login2.get(8)
        if isinstance(jwt2, bytes):
            try:
                jwt2 = jwt2.decode("utf-8", errors="ignore")
            except Exception:
                jwt2 = ""
        if not jwt2:
            return {"success": False, "error": "login_failed", "developer": DEVELOPER}

        client_url = None
        v = login2.get(10) if isinstance(login2, dict) else None
        if isinstance(v, str) and v.startswith("http"):
            client_url = v
        if not client_url:
            client_url = client_endpoint(region)

        ip = safe_choice(iP_aDdReSsEs, "151.158.158.220")
        getlogin_payload = major_login_body(access_token, open_id, 4, region, ip)
        getlogin_enc = eNcRyPt_aEs(aSsEmBlE_pRoTo(getlogin_payload))

        try:
            login_data = send_get_login_data(session, client_url, jwt2, getlogin_enc, unity_ua)
        except Exception:
            return {"success": False, "error": "login_data_failed", "developer": DEVELOPER}

        if not login_data or not login_data.get("functional_addrs"):
            return {"success": False, "error": "login_data_failed", "developer": DEVELOPER}

        new_lock = jWt_ReGiOn(jwt2)
        ok = bool(new_lock) and str(new_lock).upper() == target

        if ok:
            return {
                "success":    True,
                "message":    "region updated successfully",
                "region":     target,
                "uid":        uid,
                "jwt":        jwt2,
                "login_data": login_data,
                "developer":  DEVELOPER,
            }

        return {"success": False, "error": "region_bind_rejected", "developer": DEVELOPER}

    except BaseException:
        return {"success": False, "error": "internal_error", "developer": DEVELOPER}
    finally:
        try:
            if session is not None:
                session.close()
        except BaseException:
            pass


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
        except BaseException:
            try:
                self._send(200, safe_json({
                    "success": False,
                    "error": "internal_error",
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
        _reset_timer()

        raw_path = "/"
        params = {}
        try:
            parsed = urlparse(self.path or "/")
            raw_path = parsed.path or "/"
            params = {k: v[0] for k, v in parse_qs(parsed.query or "").items()}
        except BaseException:
            raw_path, params = "/", {}

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

        if len(uid) > MAX_UID_LEN:       uid = uid[:MAX_UID_LEN]
        if len(password) > MAX_PWD_LEN:  password = password[:MAX_PWD_LEN]
        if len(region) > MAX_REGION_LEN: region = region[:MAX_REGION_LEN]

        force = str(params.get("force", "") or "").strip().lower() in ("1", "true", "yes")

        path = raw_path.rstrip("/") or "/"
        explicit = str(params.pop("__path", "") or "").strip()
        if explicit:
            if not explicit.startswith("/"):
                explicit = "/" + explicit
            path = explicit.rstrip("/") or "/"
        elif path in ("/index.py", "/index", "/api", "/api/index", "/api/index.py"):
            path = "/bind" if (uid or password or region) else "/"

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
                    "developer": DEVELOPER,
                }))
                return

            if region not in lAnGuAgE_bY_rEgIoN:
                self._send(200, safe_json({
                    "success": False,
                    "error": "invalid_region",
                    "supported_regions": sorted(lAnGuAgE_bY_rEgIoN.keys()),
                    "developer": DEVELOPER,
                }))
                return

            try:
                result = _execute(uid, password, region, force=force)
            except BaseException:
                result = {"success": False, "error": "internal_error", "developer": DEVELOPER}

            if not isinstance(result, dict):
                result = {"success": False, "error": "internal_error", "developer": DEVELOPER}

            result.setdefault("developer", DEVELOPER)
            self._send(200, safe_json(result))
            return

        if path == "/":
            self._send(200, safe_json(HOME_INFO, indent=2))
            return

        self._send(200, safe_json({
            "success": False,
            "error": "unknown_endpoint",
            "valid_endpoints": {"home": "/", "bind": "/bind"},
            "developer": DEVELOPER,
        }))
