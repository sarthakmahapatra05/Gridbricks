import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
import websockets

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUTPUT_DIR = r"c:\Users\sarth\Desktop\Gridbricks\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

RESOLUTIONS = [
    {"name": "1440x900", "width": 1440, "height": 900, "mobile": False},
    {"name": "390x844", "width": 390, "height": 844, "mobile": True},
]

SECTIONS = [
    ("section1_decision", "section-decision"),
    ("section2_selected_day", "section-selected-day"),
    ("section3_benchmark", "section-benchmark"),
    ("section4_methodology", "section-methodology"),
]

async def capture_all():
    port = 9222
    edge_proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        f"--remote-debugging-port={port}",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-scrollbars",
        "about:blank"
    ])

    try:
        ws_url = None
        for _ in range(30):
            try:
                req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1)
                data = json.loads(req.read().decode())
                ws_url = data.get("webSocketDebuggerUrl")
                if ws_url:
                    break
            except Exception:
                await asyncio.sleep(0.5)

        if not ws_url:
            print("Failed to get WebSocket debugger URL from Edge")
            return

        print(f"Connected to Edge CDP at: {ws_url}")

        async with websockets.connect(ws_url, max_size=50_000_000) as ws:
            msg_id = 0
            async def send_cmd(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == msg_id:
                        return resp.get("result", {})

            create_res = await send_cmd("Target.createTarget", {"url": "http://localhost:3000"})
            target_id = create_res["targetId"]

            attach_res = await send_cmd("Target.attachToTarget", {"targetId": target_id, "flatten": True})
            session_id = attach_res["sessionId"]

            async def send_page_cmd(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "sessionId": session_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == msg_id:
                        return resp.get("result", {})

            await send_page_cmd("Page.enable")
            await send_page_cmd("DOM.enable")

            await send_page_cmd("Page.navigate", {"url": "http://localhost:3000"})
            await asyncio.sleep(3)

            for res in RESOLUTIONS:
                r_name = res["name"]
                w = res["width"]
                h = res["height"]
                mobile = res["mobile"]
                print(f"\n--- Testing resolution {r_name} ({w}x{h}, mobile={mobile}) ---")

                await send_page_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": w,
                    "height": h,
                    "deviceScaleFactor": 1,
                    "mobile": mobile,
                })
                await send_page_cmd("Emulation.setVisibleSize", {"width": w, "height": h})
                await asyncio.sleep(0.5)

                for sec_name, sec_id in SECTIONS:
                    eval_js = f"""
                    (function() {{
                        const el = document.getElementById('{sec_id}');
                        if (el) {{
                            el.scrollIntoView({{ behavior: 'instant', block: 'start' }});
                            return true;
                        }}
                        return false;
                    }})()
                    """
                    await send_page_cmd("Runtime.evaluate", {"expression": eval_js})
                    await asyncio.sleep(0.6)

                    shot_res = await send_page_cmd("Page.captureScreenshot", {"format": "png"})
                    img_bytes = base64.b64decode(shot_res["data"])
                    file_path = os.path.join(OUTPUT_DIR, f"{r_name}_{sec_name}.png")
                    with open(file_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"Captured: {file_path} ({len(img_bytes)} bytes)")

                eval_footer = """
                (function() {
                    const el = document.querySelector('.site-footer');
                    if (el) {
                        el.scrollIntoView({ behavior: 'instant', block: 'start' });
                        return true;
                    }
                    return false;
                })()
                """
                await send_page_cmd("Runtime.evaluate", {"expression": eval_footer})
                await asyncio.sleep(0.6)
                shot_res = await send_page_cmd("Page.captureScreenshot", {"format": "png"})
                img_bytes = base64.b64decode(shot_res["data"])
                file_path = os.path.join(OUTPUT_DIR, f"{r_name}_footer.png")
                with open(file_path, "wb") as f:
                    f.write(img_bytes)
                print(f"Captured: {file_path} ({len(img_bytes)} bytes)")

                if mobile:
                    open_drawer_js = """
                    (function() {
                        const btn = document.querySelector('.mobile-menu-trigger');
                        if (btn) btn.click();
                    })()
                    """
                    await send_page_cmd("Runtime.evaluate", {"expression": open_drawer_js})
                    await asyncio.sleep(0.6)
                    shot_res = await send_page_cmd("Page.captureScreenshot", {"format": "png"})
                    img_bytes = base64.b64decode(shot_res["data"])
                    file_path = os.path.join(OUTPUT_DIR, f"{r_name}_mobile_drawer.png")
                    with open(file_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"Captured: {file_path} ({len(img_bytes)} bytes)")

        print("\nAll screenshots captured successfully!")

    finally:
        edge_proc.terminate()
        edge_proc.wait()

if __name__ == "__main__":
    asyncio.run(capture_all())
