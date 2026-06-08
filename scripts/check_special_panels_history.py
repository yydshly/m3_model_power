"""
Guard: special panels (StreamPanel, ChatPanel, UploadPanel) participate in history flow.

Checks (P1-5):
  1. StreamPanel must import buildDemoPayload
  2. StreamPanel must NOT use cap.example directly for body initialization
  3. StreamPanel must import validatePayloadForCapability
  4. StreamPanel must support onDone prop
  5. ChatPanel must support onDone prop
  6. Capability.tsx passes onDone to ChatPanel
  7. Capability.tsx passes onDone to StreamPanel
  8. Capability.tsx passes onDone to UploadPanel
  9. UploadPanel must have confirmAssetSource state
 10. UploadPanel must call uploadCapability(..., confirmAssetSource)
 11. backend/app/routers/stream.py must call append_history
 12. backend/app/routers/upload.py must return history_id in responses
 13. InvocationHistoryPanel must include stream/upload in ACTION_LABELS
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
FRONTEND_SRC = ROOT / "frontend" / "src"
BACKEND_APP = ROOT / "backend" / "app"

def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)

def pass_check(msg: str) -> None:
    print(f"  PASS: {msg}")

def main() -> None:
    errors = 0

    # ── 1. StreamPanel imports buildDemoPayload ──────────────────────────
    sp = FRONTEND_SRC / "components" / "StreamPanel.tsx"
    content = sp.read_text(encoding="utf-8")
    if "buildDemoPayload" in content:
        pass_check("StreamPanel imports buildDemoPayload")
    else:
        print("FAIL: StreamPanel does not import buildDemoPayload")
        errors += 1

    # ── 2. StreamPanel does NOT use cap.example directly ──────────────────
    # Should be buildDemoPayload(cap), not cap.example
    if re.search(r'JSON\.stringify\s*\(\s*cap\.example\s*\*?\??\s*\{\}', content):
        print("FAIL: StreamPanel still uses cap.example directly for body init")
        errors += 1
    else:
        pass_check("StreamPanel does not use cap.example directly")

    # ── 3. StreamPanel imports validatePayloadForCapability ─────────────────
    if "validatePayloadForCapability" in content:
        pass_check("StreamPanel imports validatePayloadForCapability")
    else:
        print("FAIL: StreamPanel does not import validatePayloadForCapability")
        errors += 1

    # ── 4. StreamPanel supports onDone prop ───────────────────────────────
    if re.search(r'onDone\??:\s*\(\s*info\??:\s*\{[^}]*history_id', content) or \
       re.search(r'onDone\??:\s*\(\s*info\??:\s*\?\{[^}]*history_id', content) or \
       re.search(r'onDone\??:\s*\(\s*info', content):
        pass_check("StreamPanel onDone prop is defined")
    elif "onDone?" in content and "capability_id" in content:
        pass_check("StreamPanel onDone prop is used")
    else:
        print("FAIL: StreamPanel does not support onDone prop")
        errors += 1

    # ── 5. ChatPanel supports onDone prop ────────────────────────────────
    cp = FRONTEND_SRC / "components" / "ChatPanel.tsx"
    cp_content = cp.read_text(encoding="utf-8")
    if "onDone?" in cp_content or "onDone:" in cp_content:
        pass_check("ChatPanel supports onDone prop")
    else:
        print("FAIL: ChatPanel does not support onDone prop")
        errors += 1

    # ── 6. Capability.tsx passes onDone to ChatPanel ─────────────────────
    cap_tsx = FRONTEND_SRC / "pages" / "Capability.tsx"
    cap_content = cap_tsx.read_text(encoding="utf-8")
    if re.search(r'<ChatPanel[^>]*onDone=', cap_content):
        pass_check("Capability.tsx passes onDone to ChatPanel")
    else:
        print("FAIL: Capability.tsx does not pass onDone to ChatPanel")
        errors += 1

    # ── 7. Capability.tsx passes onDone to StreamPanel ───────────────────
    if re.search(r'<StreamPanel[^>]*onDone=', cap_content):
        pass_check("Capability.tsx passes onDone to StreamPanel")
    else:
        print("FAIL: Capability.tsx does not pass onDone to StreamPanel")
        errors += 1

    # ── 8. Capability.tsx passes onDone to UploadPanel ──────────────────
    if re.search(r'<UploadPanel[^>]*onDone=', cap_content):
        pass_check("Capability.tsx passes onDone to UploadPanel")
    else:
        print("FAIL: Capability.tsx does not pass onDone to UploadPanel")
        errors += 1

    # ── 9. UploadPanel has confirmAssetSource state ─────────────────────
    up = FRONTEND_SRC / "components" / "UploadPanel.tsx"
    up_content = up.read_text(encoding="utf-8")
    if "confirmAssetSource" in up_content:
        pass_check("UploadPanel has confirmAssetSource state")
    else:
        print("FAIL: UploadPanel does not have confirmAssetSource state")
        errors += 1

    # ── 10. UploadPanel calls uploadCapability with confirmAssetSource ──────
    if re.search(r'uploadCapability\s*\([^)]*confirmAssetSource', up_content):
        pass_check("UploadPanel calls uploadCapability(..., confirmAssetSource)")
    else:
        print("FAIL: UploadPanel does not pass confirmAssetSource to uploadCapability")
        errors += 1

    # ── 11. backend stream.py calls append_history ────────────────────────
    stream_py = BACKEND_APP / "routers" / "stream.py"
    stream_content = stream_py.read_text(encoding="utf-8")
    if "append_history" in stream_content:
        pass_check("backend/app/routers/stream.py calls append_history")
    else:
        print("FAIL: backend/app/routers/stream.py does not call append_history")
        errors += 1

    # ── 12. backend upload.py returns history_id ─────────────────────────
    upload_py = BACKEND_APP / "routers" / "upload.py"
    upload_content = upload_py.read_text(encoding="utf-8")
    if "history_id" in upload_content and 'content["history_id"]' in upload_content:
        pass_check("backend/app/routers/upload.py returns history_id in response")
    else:
        print("FAIL: backend/app/routers/upload.py does not return history_id in response")
        errors += 1

    # ── 13. InvocationHistoryPanel includes stream/upload ACTION_LABELS ────
    ihp = FRONTEND_SRC / "components" / "InvocationHistoryPanel.tsx"
    ihp_content = ihp.read_text(encoding="utf-8")
    # Use a span-based match: find the opening { after ACTION_LABELS = and count braces
    idx = ihp_content.find('ACTION_LABELS')
    if idx < 0:
        print("FAIL: Could not find ACTION_LABELS in InvocationHistoryPanel")
        errors += 1
    else:
        # Find the first { after "ACTION_LABELS"
        brace_start = ihp_content.find('{', idx)
        if brace_start < 0:
            print("FAIL: Could not find opening brace for ACTION_LABELS")
            errors += 1
        else:
            # Count braces to find the matching closing brace
            depth = 0
            i = brace_start
            while i < len(ihp_content):
                c = ihp_content[i]
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            labels_block = ihp_content[brace_start:i+1]
            # JS keys are unquoted identifiers, so check for colon-suffixed word boundary
            if re.search(r'\bstream\s*:', labels_block):
                pass_check("InvocationHistoryPanel ACTION_LABELS includes stream")
            else:
                print("FAIL: InvocationHistoryPanel ACTION_LABELS does not include stream")
                errors += 1
            if re.search(r'\bupload\s*:', labels_block):
                pass_check("InvocationHistoryPanel ACTION_LABELS includes upload")
            else:
                print("FAIL: InvocationHistoryPanel ACTION_LABELS does not include upload")
                errors += 1

    # ── Summary ──────────────────────────────────────────────────────────
    if errors == 0:
        print(f"\nAll {errors} checks passed.")
        sys.exit(0)
    else:
        print(f"\n{errors} check(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
