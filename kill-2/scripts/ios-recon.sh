#!/bin/sh
# kill-2 ios-recon.sh — IPA 快速分析脚本
# 用法: ./ios-recon.sh <path/to/app.ipa>

set -e

IPA="$1"
TMPDIR="/tmp/ios_recon_$$"

if [ -z "$IPA" ] || [ ! -f "$IPA" ]; then
    echo "[-] Usage: $0 <path/to/app.ipa>"
    exit 1
fi

echo "[*] Analyzing: $IPA"
mkdir -p "$TMPDIR"
unzip -q "$IPA" -d "$TMPDIR" 2>/dev/null || { echo "[-] Not a valid IPA"; rm -rf "$TMPDIR"; exit 1; }

# 查找主二进制
APP_DIR=$(find "$TMPDIR" -maxdepth 2 -name "*.app" -type d | head -1)
if [ -z "$APP_DIR" ]; then
    echo "[-] No .app bundle found"
    rm -rf "$TMPDIR"
    exit 1
fi

BINARY=$(find "$APP_DIR" -maxdepth 1 -type f -perm +111 | head -1 2>/dev/null)
[ -z "$BINARY" ] && BINARY=$(find "$APP_DIR" -maxdepth 1 -type f ! -name ".*" ! -name "*.plist" ! -name "*.png" ! -name "*.lproj" ! -name "*.framework" ! -name "*.dylib" | head -1)

if [ -z "$BINARY" ]; then
    # 尝试找可执行文件
    BINARY=$(find "$APP_DIR" -maxdepth 1 -type f | head -20 | while read f; do
        file "$f" | grep -q "Mach-O" && echo "$f" && break
    done)
fi

echo ""
echo "========================================"
echo "[+] Binary: $BINARY"
echo "========================================"

# Mach-O 基本信息
echo ""
echo "--- Architecture & Encryption ---"
otool -hv "$BINARY" 2>/dev/null || echo "  (otool not available)"
CRYPT=$(otool -l "$BINARY" 2>/dev/null | grep -A4 "LC_ENCRYPTION_INFO" | grep cryptid | awk '{print $2}')
if [ "$CRYPT" = "1" ]; then
    echo "  🔒 Encrypted (cryptid=1) — needs decryption"
elif [ "$CRYPT" = "0" ]; then
    echo "  ✅ Decrypted (cryptid=0)"
fi

echo ""
echo "--- Entitlements ---"
# 从 embedded.mobileprovision 或直接 codesign
if [ -f "$APP_DIR/embedded.mobileprovision" ]; then
    echo "  Provisioning profile found"
    security cms -D -i "$APP_DIR/embedded.mobileprovision" 2>/dev/null | \
        plutil -extract Entitlements xml1 -o - - 2>/dev/null | \
        grep -E '<key>|<string>' | head -30 || echo "  (plutil not available)"
fi

# 尝试 codesign 读取
codesign -d --entitlements - "$BINARY" 2>/dev/null | plutil -p - 2>/dev/null | head -30 || true

echo ""
echo "--- Frameworks & Libraries ---"
find "$APP_DIR/Frameworks" -name "*.framework" -type d 2>/dev/null | while read fw; do
    fw_name=$(basename "$fw" .framework)
    echo "  📦 $fw_name"
    # 检查是否有加密
    fw_bin="$fw/$fw_name"
    if [ -f "$fw_bin" ]; then
        fw_crypt=$(otool -l "$fw_bin" 2>/dev/null | grep -A4 "LC_ENCRYPTION_INFO" | grep cryptid | awk '{print $2}')
        [ "$fw_crypt" = "1" ] && echo "      🔒 Encrypted"
    fi
done

echo ""
echo "--- URL Schemes ---"
plutil -p "$APP_DIR/Info.plist" 2>/dev/null | grep -A2 "CFBundleURLSchemes" | head -10 || \
    /usr/libexec/PlistBuddy -c "Print :CFBundleURLTypes" "$APP_DIR/Info.plist" 2>/dev/null || \
    echo "  (Info.plist parsing skipped)"

echo ""
echo "--- External Accessory / Bonjour ---"
plutil -p "$APP_DIR/Info.plist" 2>/dev/null | grep -E "UISupportedExternalAccessoryProtocols|NSBonjourServices" | head -5 || true

echo ""
echo "--- Universal Links ---"
find "$APP_DIR" -name "apple-app-site-association*" -o -name "*.entitlements" 2>/dev/null | head -5
# 从 entitlements 读
codesign -d --entitlements - "$BINARY" 2>/dev/null | plutil -p - 2>/dev/null | grep -i "universal\|associated" | head -5 || true

echo ""
echo "--- Keychain Access Groups ---"
codesign -d --entitlements - "$BINARY" 2>/dev/null | plutil -p - 2>/dev/null | grep -i "keychain-access-groups" | head -5 || true

echo ""
echo "--- Objective-C Classes (class-dump) ---"
if command -v class-dump >/dev/null 2>&1; then
    class-dump "$BINARY" 2>/dev/null | head -30
    echo "  ... (class-dump complete)"
else
    echo "  (class-dump not installed)"
fi

echo ""
echo "--- Interesting Strings ---"
strings "$BINARY" 2>/dev/null | grep -iE \
    "password|token|secret|key|jail|debug|cydia|substrate|ptrace|inject|hook|encrypt|decrypt|cert|pinning|ssl|https|faceid|touchid|biometric|urlscheme|universallink" \
    | sort -u | head -40 || echo "  (no strings tool)"

echo ""
echo "========================================"
echo "[+] Recon complete for: $(basename "$IPA" .ipa)"
echo "========================================"

# Cleanup
rm -rf "$TMPDIR"
