#!/usr/bin/env python3
"""
ios-quick-scan.py — iOS IPA 快速分析 (纯 Python, 无外部依赖)
在 iSH Alpine 内直接运行，不需要 macOS

用法:
  python3 ios-quick-scan.py path/to/app.ipa
  python3 ios-quick-scan.py --unpack path/to/app.ipa  # 只解压
  python3 ios-quick-scan.py --json  # JSON 输出
"""
import json
import os
import re
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path

# ── SDK 签名数据库 ──
SDK_SIGNATURES = {
    "Firebase": ["Firebase", "FIRApp", "GoogleService-Info"],
    "Facebook": ["FBSDK", "FacebookSDK", "FBAudienceNetwork"],
    "Adjust": ["Adjust", "ADJEvent"],
    "AppsFlyer": ["AppsFlyer", "OneLink"],
    "Flutter": ["FlutterAppDelegate", "FlutterEngine"],
    "ReactNative": ["ReactNative", "RCTBridgeModule"],
    "Unity": ["UnityFramework", "UnityAppController"],
    "Alamofire": ["Alamofire", "AFNetworking"],
    "Moya": ["MoyaProvider"],
    "Realm": ["RLMObject", "RealmSwift"],
    "Stripe": ["Stripe", "STPPayment"],
    "Amplitude": ["Amplitude", "AMPIdentify"],
    "Mixpanel": ["Mixpanel", "MPTweak"],
}

# ── 正则 ⚠️ 密钥扫描规则 ──
SECRET_PATTERNS = [
    (r'(?:AKIA|ASIA)[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'(?:aws[_\-\.]?(?:secret|access|key|token))["\']?\s*[:=]\s*["\']?[A-Za-z0-9/+=]{40}', "AWS Secret Key"),
    (r'AIza[0-9A-Za-z\-_]{35}', "Firebase / GCP API Key"),
    (r'(?:sk_live|pk_live)_[0-9a-zA-Z]{24,}', "Stripe Live Key"),
    (r'sk-[0-9a-zA-Z]{32,}', "OpenAI API Key"),
    (r'gh[pousr]_[0-9a-zA-Z]{36}', "GitHub Token"),
    (r'(?:api_key|apikey|api[_-]?secret)["\']?\s*[:=]\s*["\']([^"\']{16,})', "Generic API Key"),
    (r'(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\']{8,})', "Potential Password"),
    (r'(?:secret|token|credential)["\']?\s*[:=]\s*["\']([^"\']{16,})', "Potential Secret/Token"),
]

# ── 保护机制启发式特征 ──
_PROTECTION_CHECKS = [
    ("PTSecurity", "PTFirmwarePass", "Fingerprint"),
    ("AntiDebug", "ptrace", "DenyDebug"),
    ("JailbreakDetection", "isJailbroken", "Cydia", "apt-get"),
    ("SSLPinning", "kSecTrustOption", "AFSecurityPolicy"),
    ("Encryption", "CCCrypt", "CommonCrypto"),
    ("Obfuscation", "_0x", "obfuscate", "mangle"),
]

def unpack_ipa(ipa_path, output_dir=None):
    """解包 IPA 到临时目录"""
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        extract_to = output_dir
    else:
        extract_to = tempfile.mkdtemp(prefix="ipa_")
    
    with zipfile.ZipFile(ipa_path, 'r') as zf:
        # Find .app directory
        app_dirs = [n for n in zf.namelist() if n.endswith('.app/')]
        if not app_dirs:
            print("⚠️  No .app directory found in IPA")
            return None, extract_to
        zf.extractall(extract_to)
    
    # Find actual .app path
    for root, dirs, _ in os.walk(extract_to):
        for d in dirs:
            if d.endswith('.app'):
                return os.path.join(root, d), extract_to
    return None, extract_to

def parse_infoplist(info_plist_path):
    """简易 Info.plist 解析 (二进制 plist 需要 plistlib)"""
    results = {}
    try:
        import plistlib
        with open(info_plist_path, 'rb') as f:
            pl = plistlib.load(f)
        results['bundle_id'] = pl.get('CFBundleIdentifier', '')
        results['version'] = pl.get('CFBundleShortVersionString', '')
        results['build'] = pl.get('CFBundleVersion', '')
        results['min_os'] = pl.get('MinimumOSVersion', '')
        results['url_schemes'] = []
        for st in pl.get('CFBundleURLTypes', []):
            for scheme in st.get('CFBundleURLSchemes', []):
                results['url_schemes'].append(scheme)
        results['universal_links'] = []
        for domain in pl.get('com.apple.developer.associated-domains', []):
            results['universal_links'].append(domain)
        results['permissions'] = {}
        for k, v in pl.items():
            if k.startswith('NS') and k.endswith('UsageDescription'):
                results['permissions'][k] = v
    except Exception:
        # Fallback: try parsing as XML
        with open(info_plist_path, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        results['_raw'] = text[:2000]
    return results

def scan_strings(app_path):
    """扫描二进制 / .dylib 文件中的字符串"""
    results = {
        'api_endpoints': [],
        'secrets': [],
        'frameworks': [],
        'urls': [],
    }
    url_pattern = re.compile(rb'https?://[^\s"\'<>]{5,200}')
    endpoint_pattern = re.compile(rb'/(?:api|v[0-9]+|rest|graphql)[/\w\-\.]{2,100}')
    
    for root, _, files in os.walk(app_path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.getsize(fp) > 5_000_000:  # skip >5MB
                continue
            try:
                with open(fp, 'rb') as fh:
                    data = fh.read(1_000_000)  # read first 1MB
            except:
                continue
            
            # SDK detection (package names in filenames)
            for sdk, sigs in SDK_SIGNATURES.items():
                if any(s.encode() in data for s in sigs):
                    if sdk not in results['frameworks']:
                        results['frameworks'].append(sdk)
            
            # URLs
            for m in url_pattern.findall(data):
                u = m.decode('utf-8', errors='replace')
                if u not in results['urls']:
                    results['urls'].append(u)
            
            # API endpoints
            for m in endpoint_pattern.findall(data):
                u = m.decode('utf-8', errors='replace')
                if u not in results['api_endpoints']:
                    results['api_endpoints'].append(u)
            
            # Secrets
            text = data.decode('utf-8', errors='replace')
            for pat, name in SECRET_PATTERNS:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    results['secrets'].append({
                        'type': name,
                        'match': m.group(0)[:40] + '...' if len(m.group(0)) > 40 else m.group(0),
                        'file': f,
                    })
    
    results['urls'] = results['urls'][:50]
    results['api_endpoints'] = results['api_endpoints'][:50]
    return results

def detect_protections(app_path):
    """检测保护机制"""
    protections = []
    for root, _, files in os.walk(app_path):
        for f in files:
            if not f.endswith(('.dylib', '')):
                continue
            fp = os.path.join(root, f)
            if os.path.getsize(fp) > 10_000_000:
                continue
            try:
                with open(fp, 'rb') as fh:
                    data = fh.read(500_000)
            except:
                continue
            text = data.decode('utf-8', errors='replace')
            for name, *sigs in _PROTECTION_CHECKS:
                if any(s in text for s in sigs):
                    protections.append({'name': name, 'file': f})
    return protections

def quick_scan(ipa_path, output_json=None):
    """主入口"""
    print(f"📱  iOS Quick Scan: {ipa_path}")
    print(f"{'='*50}")
    
    app_dir, tmpdir = unpack_ipa(ipa_path)
    if not app_dir:
        print("❌  Failed to unpack IPA")
        return
    
    info_plist = os.path.join(os.path.dirname(app_dir), 'Payload', 
                               os.path.basename(app_dir), 'Info.plist')
    if not os.path.exists(info_plist):
        info_plist = os.path.join(os.path.dirname(app_dir), os.path.basename(app_dir), 'Info.plist')
    
    report = {'app_name': os.path.basename(app_dir).replace('.app', '')}
    
    # Info.plist
    if os.path.exists(info_plist):
        plist_info = parse_infoplist(info_plist)
        report['bundle_id'] = plist_info.get('bundle_id', '')
        report['version'] = plist_info.get('version', '')
        report['build'] = plist_info.get('build', '')
        report['min_os'] = plist_info.get('min_os', '')
        report['url_schemes'] = plist_info.get('url_schemes', [])
        report['universal_links'] = plist_info.get('universal_links', [])
        print(f"  Bundle ID: {report['bundle_id']}")
        print(f"  Version: {report['version']} (build {report['build']})")
        print(f"  Min iOS: {report['min_os']}")
        if report['url_schemes']:
            print(f"  URL Schemes: {', '.join(report['url_schemes'])}")
        if report['universal_links']:
            print(f"  Universal Links: {', '.join(report['universal_links'])}")
    else:
        print("  ⚠️  No Info.plist found")
    
    # String scan
    print("\n🔍  Scanning binary strings...")
    scan = scan_strings(app_dir)
    report['frameworks'] = scan['frameworks']
    report['urls'] = scan['urls'][:10]
    report['api_endpoints'] = scan['api_endpoints'][:10]
    report['secrets'] = scan['secrets']
    
    if scan['frameworks']:
        print(f"  SDKs detected: {', '.join(scan['frameworks'])}")
    if scan['urls']:
        print(f"  URLs ({len(scan['urls'])} found, showing first 10):")
        for u in scan['urls'][:10]:
            print(f"    {u}")
    if scan['api_endpoints']:
        print(f"  API endpoints ({len(scan['api_endpoints'])} found, showing first 10):")
        for e in scan['api_endpoints'][:10]:
            print(f"    {e}")
    
    # Secrets
    secrets = scan['secrets']
    if secrets:
        print(f"\n🚨  Possible Secrets ({len(secrets)}):")
        for s in secrets:
            print(f"    [{s['type']}] {s['match']} (in {s['file']})")
    
    # Protections
    protections = detect_protections(app_dir)
    report['protections'] = protections
    if protections:
        print(f"\n🛡️  Protection Mechanisms ({len(protections)}):")
        for p in protections:
            print(f"    {p['name']} (in {p['file']})")
    else:
        report['protection_score'] = 0
        print("\n🛡️  No common protections detected")
    
    # Cleanup temp
    if not output_json:
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    # Output report
    if output_json:
        report_path = output_json
    else:
        report_path = f"{report['app_name']}-quick-report.json"
    
    # Build summary
    report['summary'] = {
        'total_urls': len(scan['urls']),
        'total_api_endpoints': len(scan['api_endpoints']),
        'total_secrets': len(secrets),
        'total_protections': len(protections),
        'risk_flags': []
    }
    if secrets:
        report['summary']['risk_flags'].append(f"{len(secrets)} hardcoded secrets")
    if report.get('url_schemes'):
        report['summary']['risk_flags'].append(f"URL schemes: {report['url_schemes']}")
    if protections:
        report['summary']['risk_flags'].append(f"Protections: {[p['name'] for p in protections]}")
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n📄  Report saved: {report_path}")
    
    if output_json:
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    return report

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 ios-quick-scan.py <ipa_path> [--json output.json]")
        sys.exit(1)
    
    ipa = sys.argv[1]
    if not os.path.exists(ipa):
        print(f"❌  File not found: {ipa}")
        sys.exit(1)
    
    json_out = None
    if '--json' in sys.argv:
        idx = sys.argv.index('--json')
        if idx + 1 < len(sys.argv):
            json_out = sys.argv[idx + 1]
    
    quick_scan(ipa, json_out)
