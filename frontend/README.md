# 浏览器前端

本目录提供 Vue 3、TypeScript 和 Vite 应用骨架，包含登录表单、身份恢复、角色导航、会员本人资料与订单入口，以及公共加载、空结果和错误组件。认证请求连接后端 `/api/auth/login`、`/api/auth/me` 和 `/api/auth/logout`；业务页面显示准备中状态。后端认证 Logic 仍有占位方法，成功登录需在该依赖完成后联调。

## 安装与运行

准备 Node.js 20.x（至少 20.19）、22.x（至少 22.12）或 24 以上版本，并使用 Node.js 自带的 npm。以下命令在仓库的 `frontend/` 目录执行；依赖版本由 `package-lock.json` 固定。

已验证的安装、检查命令：

```powershell
npm ci --cache ../tmp/npm-cache
npm run build
npm test
```

`build` 先进行 TypeScript 类型检查，再把静态资源输出到 `dist/`。`test` 使用 Vitest 执行单元、组件和角色路由测试。

开发服务器命令已验证可启动：

```powershell
Copy-Item .env.example .env.local
npm run dev
```

打开 `http://127.0.0.1:5173`，应进入登录页。开发服务器默认把 `/api` 请求代理到 `http://127.0.0.1:8000`。按后端参与说明准备数据库、环境变量和 API 服务后，再执行真实认证联调。

`.env.local` 中，`API_PROXY_TARGET` 设置开发代理目标，`VITE_API_BASE_URL` 设置浏览器请求基址，默认 `/api`。跨域直连时，将后者设为包含 `/api` 的完整 URL，并在后端配置允许的浏览器来源。`VITE_` 开头的配置会进入浏览器资源，应只填写公开配置。

## 目录与职责

| 目录 | 职责 |
|---|---|
| `src/app/` | 装配 Vue、路由、Pinia 身份状态和 TanStack Query 查询缓存，展示全局错误 |
| `src/shared/api/` | Axios 请求客户端、Bearer 身份头、请求取消、HTTP 错误和公共类型 |
| `src/shared/components/` | 加载、空结果、错误和功能准备中页面 |
| `src/features/` | 按功能域组织页面、API 适配、状态与路由声明 |
| `tests/unit/` | Vitest 单元、组件、身份恢复、缓存清理和路由测试 |
| `tests/e2e/` | Playwright 浏览器骨架测试；使用模拟网络的用例名称以 `mock` 开头 |

身份凭据保存于当前标签页的 `sessionStorage`。页面刷新后先调用 `/auth/me` 复核身份，再进入角色页面；身份失效、退出或切换账号会取消旧请求并清除私有查询缓存。身份代次保护新会话，旧复核、请求和退出的迟到结果只处理原会话。角色导航提供业务入口，权限由后端校验。

API 详情使用固定对象类型，列表使用 `Page<T>` 分页结构，可空字段保留 `null`。业务 ID 通过 `EntityId` 保留规范正十进制字符串，范围为 `1`～`9223372036854775807`；Actor、路径和错误 `recordId` 使用相同规则，计数与分页保留 `number`。金额使用两位小数字符串，时间和错误动作按后端合同接入。新增领域页面时，在所属 `features/` 目录添加类型、API 和组件；列表缓存按当前账号、目标与查询条件区分。

领域表单接入时，带 `requestId` 的命令按[前端架构](../docs/architecture/frontend.md#4-api-调用约定)保存当前标签页内的待核实记录，刷新后先恢复原账号并核实原请求。当前骨架已提供身份与 HTTP 生命周期，待核实命令存储和领域重试随业务表单实现。

## 浏览器测试

Playwright 测试运行真实浏览器，覆盖登录页、404、角色拒绝，以及模拟认证响应后的刷新复核、大整数账号显示、会员资料和订单导航、401 与退出服务不可用反馈。认证响应使用模拟网络；真实认证和业务流程的端到端验收随后端实现与数据库联调执行。

本机已安装 Microsoft Edge 时，下列 PowerShell 命令已验证：

```powershell
npm run dev
```

保持开发服务器运行，在另一终端切换至 `frontend/` 目录后运行：

```powershell
$env:PLAYWRIGHT_CHANNEL = 'msedge'
npm run test:e2e -- --workers=1
```

测试会复用 `http://127.0.0.1:5173` 的本地 Vite 服务。结束后可在运行服务的终端按 Ctrl+C 关闭。

在 Windows 上运行浏览器测试时，使用两个终端分别启动 Vite 和 Playwright，可独立管理服务生命周期。

其他环境先安装 Playwright 的 Chromium 后，启动 `npm run dev` 并在另一终端运行浏览器测试。以下安装命令已提供，当前工作区采用 Edge 验证：

```powershell
npx playwright install chromium
```

安装完成后按上面的两终端步骤启动开发服务器和测试。

## 生产部署

生产静态服务托管 `dist/`，浏览器应用使用站点根路径。先准备支持静态文件与反向代理的服务器、后端 API 和域名，再在 `frontend/` 执行已经验证的 `npm run build`。将构建产物上传到静态目录，并把 `/api/` 原路径转发至后端。页面路由使用 History 模式，静态服务器应将页面地址回退到 `index.html`。

以下 Nginx 配置是待部署验证的示例；`root` 和 API 地址需替换为实际环境：

```nginx
server {
    listen 80;
    server_name localhost;
    root /srv/gym/frontend/dist;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /assets/ {
        try_files $uri =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

配置完成后，在部署环境执行 `nginx -t` 检查配置，再由服务器管理流程加载配置；该命令尚待部署环境验证。验收时应能打开 `/login`，直接刷新 `/profile` 或 `/orders/17` 应进入身份复核与对应页面，`/api/auth/me` 应由后端返回 JSON。真实登录验收需要已完成的认证 Logic 和数据库配置。

跨域直连 API 时，在构建前设置公开的 `VITE_API_BASE_URL` 并重新构建，后端配置准确的浏览器来源。下载功能接入时按 `Content-Disposition` 读取后端文件名，跨域响应头暴露配置随后端 API 合同执行。

## 常见问题

- npm 缓存目录报 `EPERM`：在 `frontend/` 执行 `npm ci --cache ../tmp/npm-cache`，使用仓库内可写缓存。
- 开发服务器提示端口占用：关闭占用 5173 的旧开发进程后重试。浏览器测试使用同一端口。
- `/api` 连接失败：确认后端已监听代理目标地址，并检查 `.env.local`；修改配置后重启开发服务器。
- 登录返回服务不可用：检查后端认证 Logic 实现与数据库初始化结果。
- Playwright 提示找不到浏览器：使用已安装的 Edge 通道，或执行 Chromium 安装命令。
- 浏览器用例通过后进程仍等待退出：检查 Playwright 自动启动的 Vite，并通过两终端方式分别管理服务和测试。
- 刷新身份失败：重新登录，并检查 `/api/auth/me` 响应与令牌有效期。
- 生产页面直接刷新返回 404：检查静态服务的 `index.html` 路由回退；API 返回 HTML 时检查 `/api/` 转发规则。

前后端合同见[前端架构](../docs/architecture/frontend.md)和[后端架构](../docs/architecture/backend.md#17-web-api)。
