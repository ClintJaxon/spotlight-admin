#!/usr/bin/env python3
"""Spotlight door label printer. v5: back to 696x271 - brother_ql hard-validates DK-1209 (62x29) images as exactly (696, 271); 271 dots along the 29mm feed is the hardware printable max.

Watches the Spotlight admin database for print requests and prints each ticket
on a Brother QL-810W over USB (DK-1209 / 62x29 die-cut labels).

Usage:
  spotlight_print.py            run the watcher (normal use, started by systemd)
  spotlight_print.py --test     print one test label right now (no internet needed)
  spotlight_print.py --dry FILE write the printer data for a PNG to FILE.qlr (no printer needed)
"""
import base64, io, json, os, re, sys, time, threading, traceback, datetime, urllib.request, urllib.error, urllib.parse

from PIL import Image, ImageDraw, ImageFont

LABEL = "62x29"            # DK-1209 die-cut, 62 mm wide x 29 mm along the feed
MODEL = "QL-810W"
DOTS = (696, 271)          # brother_ql spec for label 62x29: 696 across tape, 271 along feed - any other page size is rejected
CONF_PATH = os.environ.get("SPOTLIGHT_ENV", os.path.expanduser("~/.spotlight-print.env"))
MAX_AGE_SEC = 120      # never print a request older than this (old queue after a reboot)
POLL_SEC = 2
HB_SEC = 5


def load_conf():
    c = {}
    if os.path.exists(CONF_PATH):
        for line in open(CONF_PATH):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                c[k.strip()] = v.strip().strip('"')
    for k in list(c):
        os.environ.setdefault(k, c[k])
    return c


CONF = load_conf()
SB = os.environ.get("SB_URL", "https://wjategfxoudacannfuqd.supabase.co")
KEY = os.environ.get("SB_KEY", "sb_publishable_KxMsa3HWPNhhE7rdQ_WamA_4ZvLOYYb")
EMAIL = os.environ.get("PRINT_EMAIL", "")
PASSWORD = os.environ.get("PRINT_PASSWORD", "")
ROTATE = int(os.environ.get("ROTATE", "0"))   # 0, 90, 180, 270 - fix if labels come out turned
CUT = os.environ.get("CUT", "1") != "0"
THRESH = int(os.environ.get("THRESHOLD", "165"))  # 0-255, higher = darker print
PRINTER = os.environ.get("PRINTER", "")           # empty = auto-find the QL on USB


def log(*a):
    print(datetime.datetime.now().strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- printing
def fit_to_label(im):
    """Scale a landscape ticket picture to fit the printable area, centred on white, 1-bit."""
    im = im.convert("L")
    if ROTATE:
        im = im.rotate(-ROTATE, expand=True, fillcolor=255)
    w, h = im.size
    s = min(DOTS[0] / w, DOTS[1] / h)
    nw, nh = max(1, int(w * s)), max(1, int(h * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    page = Image.new("L", DOTS, 255)
    page.paste(im, ((DOTS[0] - nw) // 2, (DOTS[1] - nh) // 2))
    return page.point(lambda p: 255 if p > THRESH else 0).convert("1")


def build_raster(im):
    from brother_ql.raster import BrotherQLRaster
    from brother_ql.conversion import convert
    qlr = BrotherQLRaster(MODEL)
    qlr.exception_on_warning = True
    convert(qlr, [im], LABEL, cut=CUT, rotate="0", dither=False, compress=False, red=False, dpi_600=False, hq=True)
    return qlr.data


def find_printer():
    if PRINTER:
        return PRINTER
    from brother_ql.backends.helpers import discover
    devs = discover("pyusb")
    if not devs:
        raise RuntimeError("No Brother printer found on USB. Check the USB cable, power, and that the Editor Lite light is OFF.")
    return devs[0]["identifier"]


def send_to_printer(data):
    from brother_ql.backends.helpers import send
    ident = find_printer()
    res = send(instructions=data, printer_identifier=ident, backend_identifier="pyusb", blocking=True)
    if not res.get("did_print"):
        raise RuntimeError("Printer did not confirm printing: %r" % (res,))
    return res


def print_image(im):
    lab = fit_to_label(im)
    data = build_raster(lab)
    mock = os.environ.get("MOCK_PRINT_DIR")
    if mock:  # testing without a printer
        n = len(os.listdir(mock))
        lab.save(os.path.join(mock, "label%d.png" % n))
        open(os.path.join(mock, "label%d.qlr" % n), "wb").write(data)
        return
    send_to_printer(data)


def test_label():
    im = Image.new("L", (720, 330), 255)
    d = ImageDraw.Draw(im)
    d.rectangle([9, 9, 710, 320], outline=0, width=6)
    d.rectangle([22, 22, 697, 307], outline=0, width=2)
    try:
        f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except Exception:
        f1 = f2 = ImageFont.load_default()
    d.text((360, 95), "SPOTLIGHT TEST", font=f1, fill=0, anchor="mm")
    d.text((360, 165), "Door printer is working", font=f2, fill=0, anchor="mm")
    d.text((360, 215), time.strftime("%b %d %I:%M %p"), font=f2, fill=0, anchor="mm")
    d.polygon([(60, 270), (100, 250), (100, 290)], fill=0)
    d.text((115, 270), "this side first out of printer", font=ImageFont.load_default(), fill=0, anchor="lm")
    return im


# ---------------------------------------------------------------- database
class Api:
    def __init__(self):
        self.tok = None
        self.rt = None
        self.tok_at = 0

    def _req(self, method, path, body=None, headers=None, auth=True):
        h = {"apikey": KEY, "Content-Type": "application/json"}
        if auth:
            h["Authorization"] = "Bearer " + self.tok
        if headers:
            h.update(headers)
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(SB + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=20) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw.decode("utf-8", "replace")

    def login(self):
        st, j = self._req("POST", "/auth/v1/token?grant_type=password", {"email": EMAIL, "password": PASSWORD}, auth=False)
        if st != 200:
            raise RuntimeError("Sign-in failed (%s): %s" % (st, j))
        self.tok, self.rt, self.tok_at = j["access_token"], j.get("refresh_token"), time.time()
        log("signed in as", EMAIL)

    def call(self, method, path, body=None, headers=None):
        if not self.tok or time.time() - self.tok_at > 45 * 60:
            self.login()
        st, j = self._req(method, path, body, headers)
        if st == 401:
            self.login()
            st, j = self._req(method, path, body, headers)
        return st, j

    def jobs(self):
        st, j = self.call("GET", "/rest/v1/settings?select=key,value&key=like.printjob_*&order=key.asc")
        if st != 200:
            raise RuntimeError("Could not read print requests (%s): %s" % (st, j))
        return j

    def delete(self, key):
        return self.call("DELETE", "/rest/v1/settings?key=eq." + urllib.parse.quote(key))[0]

    def put(self, key, value):
        return self.call("POST", "/rest/v1/settings", {"key": key, "value": value},
                         {"Prefer": "resolution=merge-duplicates,return=minimal"})[0]


STATE = {"printed": 0, "err": "", "last": ""}


def printer_present():
    # True if the Brother shows up on USB. False only when we can enumerate
    # USB and the printer is definitely not there (never a false alarm).
    try:
        import usb.core
        vid, pid = 0x04F9, 0x209C
        m = re.match(r"^usb://(0x[0-9a-fA-F]+|[0-9a-fA-F]+):(0x[0-9a-fA-F]+|[0-9a-fA-F]+)", PRINTER or "")
        if m:
            vid, pid = int(m.group(1), 16), int(m.group(2), 16)
        return usb.core.find(idVendor=vid, idProduct=pid) is not None
    except Exception:
        return True


def heartbeat(api):
    while True:
        try:
            v = json.dumps({"v": 5, "at": datetime.datetime.utcnow().isoformat() + "Z", "printed": STATE["printed"],
                            "err": STATE["err"], "last": STATE["last"], "usb": printer_present()})
            api.put("printer_hb", v)
        except Exception as e:
            log("heartbeat failed:", e)
        time.sleep(HB_SEC)


def key_age(key):
    # printjob_<ms>_<rand>
    try:
        ms = int(key.split("_")[1])
        return time.time() - ms / 1000.0
    except Exception:
        return 0


def run():
    if not EMAIL or not PASSWORD:
        sys.exit("Set PRINT_EMAIL and PRINT_PASSWORD in " + CONF_PATH)
    done_path = os.path.expanduser("~/.spotlight-print-done.json")
    done = set(json.load(open(done_path))) if os.path.exists(done_path) else set()
    api = Api()
    api.login()
    threading.Thread(target=heartbeat, args=(api,), daemon=True).start()
    log("watching for print requests")
    while True:
        try:
            for row in api.jobs():
                key = row["key"]
                if key in done:
                    api.delete(key)
                    continue
                if key_age(key) > MAX_AGE_SEC:
                    log("skipping old request", key)
                    done.add(key)
                    api.delete(key)
                    continue
                try:
                    job = json.loads(row["value"])
                    n = 0
                    for dataurl in job.get("imgs", []):
                        png = base64.b64decode(dataurl.split(",", 1)[1])
                        print_image(Image.open(io.BytesIO(png)))
                        n += 1
                    STATE["printed"] += n
                    STATE["err"] = ""
                    STATE["last"] = (job.get("name") or "") + " x" + str(n)
                    log("printed", n, "ticket(s) for", job.get("name"))
                except Exception as e:
                    STATE["err"] = str(e)[:200]
                    log("PRINT FAILED for", key, e)
                    traceback.print_exc()
                    # one failed request is marked done so it does not loop; staff use the PDF button
                done.add(key)
                try:
                    json.dump(sorted(done)[-500:], open(done_path, "w"))
                except Exception as e:
                    log("could not save done list:", e)
                api.delete(key)
        except Exception as e:
            log("loop error:", e)
            time.sleep(5)
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--test"]:
        print_image(test_label())
        log("test label sent")
    elif a[:1] == ["--dry"] and len(a) == 2:
        data = build_raster(fit_to_label(Image.open(a[1])))
        open(a[1] + ".qlr", "wb").write(data)
        log("wrote", a[1] + ".qlr", len(data), "bytes")
    else:
        run()
