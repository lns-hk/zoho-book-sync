# Zoho Book Sync

[English](README.md) | [简体中文](README.zh-Hans.md) | [正體中文](README.zh-Hant.md) | **日本語**

Zoho Book Sync は、Zoho Books の見積書や請求書などを PDF として書き出し、コンピュータ上の任意のフォルダに顧客ごとに保存する macOS / Windows 用のデスクトップアプリです。

バージョン：0.2.0

> Zoho Book Sync は独立したプロジェクトであり、Zoho Corporation が開発・承認・サポートするものではありません。Zoho および Zoho Books は Zoho Corporation の商標です。

## 背景

私たちは複数のパートナー企業と共同でプロジェクトを進めています。これまでは Zoho Books で見積書や請求書を発行するたびに、PDF を手作業でダウンロードしてパートナーに送っており、手間がかかるうえミスも起こりがちでした。

Zoho Books の無料プランにはワークフロールールやカスタム関数がないため、Zoho の中だけでは自動化できません。そこで Zoho Book Sync がデスクトップ側で次の処理を行います。

1. Zoho Books API で新規・変更された書類を読み込みます。
2. 各書類を PDF としてダウンロードします。
3. 選んだローカルフォルダ内の該当する顧客フォルダに保存します。

保存先はどのフォルダでも構いません。パートナーに自動でファイルを届けたい場合は、OneDrive、Google Drive、Dropbox、NAS などの同期サービスが同期しているフォルダを選び、各顧客フォルダを一度パートナーと共有してください。

## 機能

- **表示言語：** 英語、簡体字中国語、繁体字中国語、日本語。既定ではシステムの言語に合わせ、「ステータス」タブの「言語」メニューからいつでも切り替えられます。
- **書類の種類：** 見積書、請求書、クレジットノート、受注書、入金領収書。同期する種類は設定で選べます。
- **3 つの同期方法：**
  - 新規を同期：新規・変更された書類のみ。通常はこちらを使います。
  - すべて同期：過去の書類もすべて同期します。
  - 選んで同期：絞り込んだ一覧から書類を選びます。
- **顧客フォルダ：**
  - 複数の Zoho の会社を 1 つのフォルダにまとめられます。
  - 登録した顧客のみ同期するよう設定できます。
  - 会社の一覧は Zoho の顧客一覧から取得し、24 時間キャッシュします。
- **書類が変更されたとき：** 既定では新しい版（`_v2.pdf`）として保存するため、手作業で編集したファイルが上書きされることはありません。上書きやスキップも選べます。
- **自動同期：**
  - 確認間隔を設定できます。
  - ログイン時に起動し、メニューバーやシステムトレイで動作します。
  - 新しいファイルやエラーを通知します。
- **API 使用量：**
  - Zoho のプランを自動で検出します。
  - ウインドウ下部に本日の API 残り回数と、このコンピュータの使用数を表示します。
  - 「自動同期」タブに各上限と、自動同期で 1 日に使う見込み回数を表示します。
- **セキュリティ：**
  - トークンはアプリ専用のフォルダにのみ保存し、システムのキーチェーンは使いません。
  - Zoho には読み取り権限のみを要求します。

## インストール

[Releases](../../releases) からダウンロードします。

| システム | ファイル | 初回起動 |
|---|---|---|
| macOS（Apple Silicon） | `ZohoBookSync-mac.zip` | 解凍して `ZohoBookSync.app` を「アプリケーション」に移動します。Apple の署名がないため、初回は**右クリック → 開く**で起動してください。 |
| Windows 10/11 | `ZohoBookSync-windows.zip` | 解凍して `ZohoBookSync\ZohoBookSync.exe` を実行します。SmartScreen の警告が出たら**詳細情報 → 実行**をクリックしてください。 |

## 使い方

### 1. Zoho に接続（「Zoho 接続」タブ）

次の 2 つの方法のどちらかを使います。

**ワンクリックサインイン（推奨）**

管理者が一度だけ設定します。
1. [Zoho API Console](https://api-console.zoho.com) で **Add Client** をクリックし、**Server-based Applications** を選びます。
2. 次のとおり入力します。
   - Homepage URL：任意の URL（例：`http://127.0.0.1:53682`）
   - Authorized Redirect URIs：`http://127.0.0.1:53682/callback`
3. Client ID と Client Secret を同僚に渡します。

各ユーザーはアプリに Client ID と Secret を入力し、「Zoho に接続」をクリックします。ブラウザで Zoho のサインインページが開くので、**Accept** をクリックすれば完了です。

**手動入力**

1. API Console で **Self Client** を作成します。
2. **Generate Code** タブにアプリに表示された Scope を貼り付け（「コピー」ボタンを使用）、Time Duration を 10 minutes にします。
3. アプリに Client ID、Client Secret、Code を入力し、「Zoho に接続」をクリックします。

接続後：
- Zoho Books の組織を選びます。
- 今日以降の新しい書類のみ同期するか、後で決めるかを選びます。

### 2.「同期設定」タブ

- **同期する書類：** 同期する種類にチェックを入れます。
- **次のステータスは同期しない：** 例：下書き、無効。
- **保存先：** コンピュータ上の任意のフォルダを指定できます。既定では、OneDrive がインストールされていれば OneDrive 内の `Zoho Books` フォルダ、なければ「書類」内の `Zoho Books` を使います。「選択…」で変更できます。
- **フォルダとファイル名：** `{partner}/{type}/{number}.pdf` のようなテンプレートで指定します。使用できる項目：`{partner}` `{company}` `{customer}` `{type}` `{number}` `{year}` `{month}` `{date}` `{status}`。

書類の種類ごとのフォルダ名（`Quotes`、`Invoices` など）は表示言語にかかわらず英語のままなので、言語を切り替えてもファイルが移動することはありません。

### 3.「顧客フォルダ」タブ

1. 「顧客を追加」をクリックし、フォルダ名を変更します。
2. 「Zoho から会社を選択…」をクリックし、この顧客に属する会社にチェックを入れます。

登録されていない会社は、会社名のフォルダに保存されます。登録した会社のみ同期する場合は「下に登録した会社のみ同期」にチェックを入れます。

### 4.「ステータス」タブ

- **新規を同期：** 新規・変更された書類を同期します。通常はこちらを使います。
- **すべて同期…：** 過去の書類もすべて同期します。
- **選んで同期…：** 期間を選んでから、同期する書類にチェックを入れます。
- **最近の履歴：** 行をダブルクリックするとファイルが開きます。
- **言語：** 表示言語を切り替えます。

### 5.「自動同期」タブ

自動同期をオンにして確認間隔を選び、必要に応じてログイン時の起動をオンにします。ウインドウを閉じても、アプリはメニューバーやシステムトレイで動作し続けます。

### API の上限

Zoho Books の 1 日の API 上限は、同僚のコンピュータや他の連携も含め **Zoho の組織全体で共有**されます。

| プラン | 1 日の上限 |
|---|---|
| Free | 1,000 |
| Standard | 2,000 |
| Professional | 5,000 |
| Premium / Elite / Ultimate | 10,000 |

アプリは Zoho の各応答に含まれる `X-Rate-Limit-*` ヘッダーを読み取り、残り回数をリアルタイムに表示します。自動同期の確認 1 回につき、書類の種類ごとに約 1 回 API を使います。

## ファイルの場所

| 用途 | macOS | Windows |
|---|---|---|
| 設定 | `~/Library/Application Support/ZohoBookSync/settings.json` | `%LOCALAPPDATA%\ZohoBookSync\settings.json` |
| トークン | `~/Library/Application Support/ZohoBookSync/secrets.json` | `%LOCALAPPDATA%\ZohoBookSync\secrets.json` |
| 同期履歴、API 使用量、会社キャッシュ | `~/Library/Application Support/ZohoBookSync/` | `%LOCALAPPDATA%\ZohoBookSync\` |
| ログ | `~/Library/Logs/ZohoBookSync/zoho_book_sync.log` | `%LOCALAPPDATA%\ZohoBookSync\Logs\zoho_book_sync.log` |

サインイン情報を消去するには、「Zoho 接続」タブで「接続を解除」をクリックするか、`secrets.json` を削除します。

### 0.1.0（ZohoSync）からのアップグレード

0.2.0 は ZohoSync から名称を変更し、データを新しい `ZohoBookSync` フォルダに保存するため、まっさらな状態で起動します。Zoho に再接続し、顧客フォルダを設定し直してください。以前の設定は引き継がれません。0.1.0 でログイン時の起動をオンにしていた場合は、先に旧バージョンでオフにする（または旧アプリを削除する）と、古い `ZohoSync` フォルダを削除できます。

## 開発

Python 3.11 以降が必要です。

```bash
python -m venv ~/.venvs/zoho-book-sync        # 仮想環境はクラウド同期フォルダの外に置いてください
~/.venvs/zoho-book-sync/bin/pip install -r requirements-dev.txt
~/.venvs/zoho-book-sync/bin/python -m pytest tests
~/.venvs/zoho-book-sync/bin/python app.py
```

### 翻訳

画面上のテキストはすべて `zoho_sync/i18n.py` にあります。1 つのテキストに 1 つのキーがあり、英語・簡体字中国語・繁体字中国語・日本語が入っています。`tests/test_i18n.py` は、コードで使われているキーがすべて存在すること、4 言語すべてが入力され `{placeholders}` が一致していること、カタログ以外にテキストがハードコードされていないことを確認します。

### パッケージ作成

対象のシステムで `python build.py` を実行します。

- macOS → `dist-mac/ZohoBookSync-mac.zip`（ad-hoc 署名）
- Windows → `dist-windows/ZohoBookSync-windows.zip`

Windows のビルドと検証の記録は [`docs/WINDOWS_BUILD.md`](docs/WINDOWS_BUILD.md) にあります。

### 構成

```
app.py                  エントリポイント：単一インスタンス、ログ、言語
zoho_sync/i18n.py       4 言語の画面テキスト、言語の検出
zoho_sync/zoho.py       Zoho OAuth と Books API クライアント（再試行、レート制限、使用量ヘッダー）
zoho_sync/engine.py     同期エンジン：書類の一覧、書き出す書類の判断、PDF の安全な書き込み
zoho_sync/config.py     設定、トークン、同期履歴、API 使用量、会社キャッシュ
zoho_sync/gui.py        PySide6 の画面（5 つのタブ、トレイアイコン、書類選択と会社選択のダイアログ）
zoho_sync/autostart.py  ログイン時の起動（macOS LaunchAgent / Windows Run key）
tests/                  pytest
```
