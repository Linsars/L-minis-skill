---
name: api-authorization-and-bola
description: >-
  API authorization and BOLA testing playbook. Use when APIs expose object identifiers, nested resources, hidden writable fields, or weak function-level authorization.
---

# SKILL: API Authorization and BOLA — Object Access, Function Access, and Mass Assignment

> **AI LOAD INSTRUCTION**: Use this skill when an API exposes object IDs, nested resources, or role-sensitive functions and you need a focused authorization test path: BOLA, BFLA, method abuse, and hidden field control.

## 1. CORE TEST LOOP

1. Create Account A and Account B.
2. As Account A, capture create, read, update, and delete flows.
3. Replay with Account B's token.
4. Test sibling endpoints, nested endpoints, and alternate HTTP verbs.

## 2. TEST SURFACES

| Surface | Example |
|---|---|
| object read | `/api/v1/orders/123` |
| nested object | `/api/v1/users/1/invoices/9` |
| admin or internal function | `/api/v1/admin/users` |
| update path | `PUT`, `PATCH`, `DELETE` variants |
| hidden JSON fields | `role`, `org`, `verified`, `tier` |

## 3. QUICK PAYLOADS

```json
{"role":"admin"}
{"isAdmin":true}
{"org":"target-company"}
{"verified":true}
```

## 4. WHAT TESTERS MISS

- object IDs in headers, cookies, GraphQL args, and nested objects
- alternate methods sharing the same route but weaker authz
- parent check present, child resource check missing
- admin docs revealing extra writable fields

## 5. NEXT ROUTING

- For JWT or token-layer abuse: [api auth and jwt abuse](../api-auth-and-jwt-abuse/SKILL.md)
- For GraphQL and hidden parameter discovery: [graphql and hidden parameters](../graphql-and-hidden-parameters/SKILL.md)
- For broader IDOR patterns outside APIs: [idor broken object authorization](../idor-broken-object-authorization/SKILL.md)

## 6. DARWIN WRAPPER

### Routing
- 只看到对象 ID、嵌套资源、可猜测主键、批量 API → 继续本 skill
- 带 JWT/OAuth 的授权问题 → 联动 `jwt-oauth-token-attacks`
- 只是字段校验或业务逻辑 bug，不涉及跨主体访问 → 不要强行套 BOLA

### Workflow
1. 先建主体矩阵：A 用户 / B 用户 / 匿名 / 低权 / 高权
2. 先测读，再测写，再测批量/嵌套/关联对象
3. 再测隐藏可写字段与状态机越权
4. 所有命中结果回写到对象关系图，不只记单个 endpoint

### CHECKPOINT
- **🔴** 没建主体矩阵前，不下结论说有/无越权
- **🛑** 只有 403/404 差异还不够，继续测 side effects
- **⚠️** 资源嵌套越深，越要测父子关系断裂

### Failure Modes
| 触发条件 | 一线修复 | 仍失败 → 兜底 |
|---|---|---|
| 直接换 ID 返回 404 | 换同租户/跨租户/已删除对象再测 | 转 side-effect / timing / write-path |
| GET 安全但 PATCH/DELETE 未测 | 立即补写路径测试 | 标记读安全写不安全 |
| 对象 ID 不可猜 | 从列表/导出/日志/前端缓存找二次来源 | 转 hidden field / nested resource |
| JWT 切换主体不便 | 造第二账号或弱权限 token | 联动 JWT/OAuth skill |

### Anti-Patterns
- 不把 404 当成无漏洞证据
- 不只测 GET 不测写路径
- 不忽略 nested resource 和 hidden writable fields
