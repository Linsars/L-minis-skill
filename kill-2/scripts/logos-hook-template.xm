/* Logos Inline Hook — 绕过 Jailbreak Detection 模板
 * kill-2 越狱 Tweak 开发 (Theos + Logos)
 * 用法: %hook 目标方法 → 替换返回值为未越狱状态
 */

%hook ClassName

/* Hook 1: 文件检测绕过 — 常见的 jailbreak 文件路径检查 */
- (BOOL)isJailbroken {
    return NO;
}

/* Hook 2: URL scheme 检测绕过 */
- (BOOL)application:(UIApplication *)app openURL:(NSURL *)url options:(NSDictionary *)opts {
    /* 拦截恶意 URL 跳转 */
    if ([[url scheme] isEqualToString:@"malicious"]) {
        return NO;
    }
    return %orig;
}

/* Hook 3: 沙箱路径检查绕过 — 拦截 NSFileManager 的敏感路径检测 */
%hook NSFileManager

- (BOOL)fileExistsAtPath:(NSString *)path {
    NSArray *jbPaths = @[@"/var/jb", @"/Applications/Cydia.app", 
                         @"Library/MobileSubstrate", @"/bin/bash",
                         @"/usr/sbin/sshd", @"/etc/apt"];
    for (NSString *jbPath in jbPaths) {
        if ([path hasPrefix:jbPath] || [path isEqualToString:jbPath]) {
            return NO;
        }
    }
    return %orig;
}

%end

/* Hook 4: sysctl 检测绕过 — ptrace/sysctl 调试器检测 */
%hookf(int, ptrace, int _request, pid_t _pid, caddr_t _addr, int _data) {
    if (_request == 31 /* PT_DENY_ATTACH */) {
        return -1;
    }
    return %orig;
}

/* Constructor — 延迟加载防扫描 */
%ctor {
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(5.0 * NSEC_PER_SEC)),
                   dispatch_get_main_queue(), ^{
        %init(ClassName);
    });
}
