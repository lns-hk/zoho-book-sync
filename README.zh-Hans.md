# Zoho Book Sync

[English](README.md) | **简体中文** | [正體中文](README.zh-Hant.md) | [日本語](README.ja.md)

Zoho Book Sync 是一款适用于 macOS 和 Windows 的桌面应用程序，可将 Zoho Books 的报价单、发票等单据导出为 PDF，并按客户分类保存到 OneDrive 或任何本地文件夹。

版本：0.2.0

> Zoho Book Sync 为独立项目，并非由 Zoho Corporation 开发、认可或提供支持。Zoho 和 Zoho Books 是 Zoho Corporation 的商标。

## 背景

我们与多家合作公司共同开展项目。过去每开一张报价单或发票，都要在 Zoho Books 手动下载 PDF，再逐份发送给合作公司，既费时又容易出错。

Zoho Books 免费方案不提供 Workflow 和 Custom Function，无法在 Zoho 内实现自动化。因此我们开发了这款桌面应用程序，流程如下：

1. 通过 Zoho Books API 读取新开或已修改的单据。
2. 将单据下载为 PDF。
3. 保存到 OneDrive 等云同步文件夹中对应的客户文件夹。
4. 由云客户端自动上传。

只需将每个客户文件夹共享给合作公司一次，此后新单据就会自动送达。

## 功能

- **界面语言：** 英文、简体中文、正体中文、日文。默认跟随系统语言，也可随时在“状态”页的“语言”菜单切换。
- **单据类型：** 报价单、发票、退款单、销售订单、收款收据，可在设置中自行选择。
- **三种同步方式：**
  - 同步新单：只同步新开和已修改的单据，供日常使用。
  - 全部同步：同步全部历史单据。
  - 自选同步：从筛选后的列表中勾选单据。
- **客户文件夹：**
  - 可将多家 Zoho 公司归入同一文件夹。
  - 可设置只同步已列出的客户。
  - 公司名单取自 Zoho 客户名册，缓存 24 小时。
- **单据修改后：** 默认另存新版本（`_v2.pdf`），不会覆盖手动修改过的文件；也可改为覆盖或跳过。
- **自动同步：**
  - 可设置检查频率。
  - 可开机自动启动，并在菜单栏或系统托盘运行。
  - 有新文件或出错时发出通知。
- **API 用量：**
  - 自动识别 Zoho 方案。
  - 窗口底部显示今日 API 剩余次数及本机用量。
  - “自动同步”页显示各项上限，以及自动同步预计每日使用的次数。
- **安全：**
  - 令牌只保存在应用程序自身的文件夹中，不使用系统钥匙串。
  - 只申请 Zoho 的只读权限。

## 安装

请从 [Releases](../../releases) 下载：

| 系统 | 文件 | 首次打开 |
|---|---|---|
| macOS（Apple Silicon） | `ZohoBookSync-mac.zip` | 解压后将 `ZohoBookSync.app` 移到“应用程序”。由于未经 Apple 签名，首次打开须**右键 → 打开**。 |
| Windows 10/11 | `ZohoBookSync-windows.zip` | 解压后运行 `ZohoBookSync\ZohoBookSync.exe`。如出现 SmartScreen 警告，请点击**更多信息 → 仍要运行**。 |

## 使用方法

### 1. 连接 Zoho（“连接 Zoho”页）

以下两种方式任选其一。

**一键登录（推荐）**

需由管理员先完成一次设置：
1. 在 [Zoho API Console](https://api-console.zoho.com) 点击 **Add Client**，选择 **Server-based Applications**。
2. 填写以下信息：
   - Homepage URL：任意网址均可，例如 `http://127.0.0.1:53682`。
   - Authorized Redirect URIs：`http://127.0.0.1:53682/callback`。
3. 将 Client ID 和 Client Secret 提供给同事。

用户在应用程序中输入 Client ID 和 Secret 后点击“连接 Zoho”，浏览器会打开 Zoho 登录页面，点击 **Accept** 即完成。

**手动输入**

1. 在 API Console 创建 **Self Client**。
2. 在 **Generate Code** 页签粘贴应用程序显示的 Scope（可点击“复制”），Time Duration 选择 10 minutes。
3. 在应用程序中输入 Client ID、Client Secret 和 Code，然后点击“连接 Zoho”。

连接成功后：
- 选择 Zoho Books 组织。
- 选择只同步今天之后的新单据，或稍后再决定。

### 2.“同步设置”页

- **同步哪些单据：** 勾选要同步的类型。
- **不同步以下状态：** 例如草稿、作废。
- **保存位置：** 默认为 OneDrive 中的 `Zoho Books` 文件夹，可点击“选择…”更改。
- **文件夹和文件名：** 用模板设置，例如 `{partner}/{type}/{number}.pdf`。可用字段：`{partner}` `{company}` `{customer}` `{type}` `{number}` `{year}` `{month}` `{date}` `{status}`。

单据类型文件夹名称（`Quotes`、`Invoices` 等）不论界面语言均保持英文，因此切换语言不会移动任何文件。

### 3.“客户文件夹”页

1. 点击“新增客户”，并修改文件夹名称。
2. 点击“从 Zoho 选择公司…”，勾选属于该客户的公司。

未列出的公司会以其公司名建立文件夹。如只需同步已列出的公司，请勾选“只同步下面列出的公司”。

### 4.“状态”页

- **同步新单：** 同步新开和已修改的单据，供日常使用。
- **全部同步…：** 同步全部历史单据。
- **自选同步…：** 选择日期范围后勾选单据。
- **最近记录：** 双击可打开文件。
- **语言：** 切换界面语言。

### 5.“自动同步”页

开启自动同步并设置检查频率，如有需要可开启“开机自动启动”。关闭窗口后，程序会继续在菜单栏或系统托盘运行。

### API 使用上限

Zoho Books 的每日 API 上限由**整个 Zoho 组织共用**，包括同事的电脑及其他集成：

| 方案 | 每日上限 |
|---|---|
| Free | 1,000 |
| Standard | 2,000 |
| Professional | 5,000 |
| Premium / Elite / Ultimate | 10,000 |

应用程序会读取 Zoho 每次响应中的 `X-Rate-Limit-*` 信息，以显示实时剩余次数。每次自动检查，每种单据类型约使用一次 API。

## 文件位置

| 用途 | macOS | Windows |
|---|---|---|
| 设置 | `~/Library/Application Support/ZohoBookSync/settings.json` | `%LOCALAPPDATA%\ZohoBookSync\settings.json` |
| 令牌 | `~/Library/Application Support/ZohoBookSync/secrets.json` | `%LOCALAPPDATA%\ZohoBookSync\secrets.json` |
| 同步记录、API 用量、公司缓存 | `~/Library/Application Support/ZohoBookSync/` | `%LOCALAPPDATA%\ZohoBookSync\` |
| 日志 | `~/Library/Logs/ZohoBookSync/zoho_book_sync.log` | `%LOCALAPPDATA%\ZohoBookSync\Logs\zoho_book_sync.log` |

如需清除登录信息，可在“连接 Zoho”页点击“断开连接”，或直接删除 `secrets.json`。

### 从 0.1.0（ZohoSync）升级

0.2.0 由 ZohoSync 更名而来，数据改存于新的 `ZohoBookSync` 文件夹，因此会以全新状态启动：请重新连接 Zoho 并设置客户文件夹，旧设置不会迁移。如曾在 0.1.0 开启开机自动启动，请先在旧版关闭（或删除旧版应用程序），之后即可删除旧的 `ZohoSync` 文件夹。

## 开发

需要 Python 3.11 或以上版本。

```bash
python -m venv ~/.venvs/zoho-book-sync        # 虚拟环境请勿放在云同步文件夹中
~/.venvs/zoho-book-sync/bin/pip install -r requirements-dev.txt
~/.venvs/zoho-book-sync/bin/python -m pytest tests
~/.venvs/zoho-book-sync/bin/python app.py
```

### 翻译

所有界面文字都在 `zoho_sync/i18n.py` 中：每段文字一个键，包含英文、简体中文、正体中文和日文。`tests/test_i18n.py` 会检查代码中使用的每个键都存在、四种语言均已填写且 `{placeholders}` 一致，以及目录以外没有写死的文字。

### 打包

在目标系统运行 `python build.py`：

- macOS → `dist-mac/ZohoBookSync-mac.zip`（ad-hoc 签名）
- Windows → `dist-windows/ZohoBookSync-windows.zip`

Windows 打包及验证记录见 [`docs/WINDOWS_BUILD.md`](docs/WINDOWS_BUILD.md)。

### 项目结构

```
app.py                  入口：单实例、日志、语言
zoho_sync/i18n.py       四种语言的界面文字、语言识别
zoho_sync/zoho.py       Zoho OAuth 和 Books API 客户端（重试、限流、读取 API 用量）
zoho_sync/engine.py     同步引擎：列出单据、决定导出项、安全写入 PDF
zoho_sync/config.py     设置、令牌、同步记录、API 用量、公司缓存
zoho_sync/gui.py        PySide6 界面（五个页签、系统托盘、自选同步和选择公司窗口）
zoho_sync/autostart.py  开机启动（macOS LaunchAgent / Windows Run key）
tests/                  pytest
```
