// Surge JavaScript MITM 重写脚本模板 — kill-2
// 注入到 .sgmodule 使用: script-name=mitm_template.js, requires-body=true
// 
// 功能模块:
//   1. API 响应拦截与修改
//   2. 请求头注入 (认证旁路)
//   3. 流式响应处理
//   4. VPN/代理 检测绕过
//   5. entitlement 伪造验证

/* ── 请求拦截 ── */
$surge.on('request', function(request) {
    let url = request.url;
    let headers = request.headers;
    let modified = false;

    // 模块1: API 请求拦截
    if (url.includes('/api/v1/validate')) {
        // 注入伪造授权头
        request.headers['X-Internal'] = 'true';
        request.headers['X-Device-Check'] = 'bypassed';
        modified = true;
    }

    // 模块2: VPN/代理检测绕过
    if (url.includes('/check/environment')) {
        // 修改 SNI 绕过检测
        request.headers['X-Forwarded-For'] = '127.0.0.1';
        modified = true;
    }

    // 模块3: 请求体修改 (仅小数据)
    if (request.body && request.body.length < 10240) {
        try {
            let body = JSON.parse(request.body.toLocaleString());
            if (body.deviceInfo) {
                body.deviceInfo.isJailbroken = false;
                body.deviceInfo.isSimulator = false;
                body = JSON.stringify(body);
                $done({body: body});
                return;
            }
        } catch(e) {}
    }

    if (modified) {
        $done({headers: request.headers});
    } else {
        $done();
    }
});

/* ── 响应拦截 ── */
$surge.on('response', function(response) {
    let url = response.request.url;
    let body = response.body ? response.body.toLocaleString() : '';
    
    // 模块4: 许可证/订阅验证绕过
    if (url.includes('/api/v1/subscription') || url.includes('/verify/receipt')) {
        try {
            let data = JSON.parse(body);
            data.status = "active";
            data.expiresDate = "2099-12-31T23:59:59Z";
            data.isTrial = false;
            data.entitlements = {
                "pro": {"expires": "2099-12-31T23:59:59Z"},
                "premium": {"expires": "2099-12-31T23:59:59Z"}
            };
            $done({body: JSON.stringify(data)});
            return;
        } catch(e) {}
    }

    // 模块5: 远程配置篡改 (开关/Feature Flag)
    if (url.includes('/api/v1/config') || url.includes('/features')) {
        try {
            let config = JSON.parse(body);
            config.features = config.features || {};
            config.features.jailbreakDetection = false;
            config.features.licenseCheck = false;
            config.features.debugMode = true;
            config.environment = "production";
            $done({body: JSON.stringify(config)});
            return;
        } catch(e) {}
    }

    // 模块6: 大文件跳过 (不修改)
    if (body.length > 1048576) {  // >1MB
        $done();
        return;
    }

    $done();
});

// .sgmodule 引用:
// [Script]
// mitm_template.js = type=http-response,pattern=^https?://api\.example\.com/.*,requires-body=true,script-path=scripts/mitm_template.js
