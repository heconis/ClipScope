# ClipScope

ClipScope は、Twitch 配信中に作成されたクリップを監視し、選択したクリップを OBS の Browser Source で再生する Windows 向けデスクトップアプリです。

## 主な機能

- Twitch Device Code Flow 認証
- ログインユーザー自身のチャンネルをポーリング監視
- クリップ一覧表示、選択、削除
- 再生済み / 未再生ステータス表示
- OBS 用ローカル再生ページ (`/obs-player`) でクリップ再生

## 開発実行

### 1. 仮想環境作成

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 依存関係インストール

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. アプリ起動

```powershell
python -m app.main --run-ui
```

## 環境変数 (任意)

`TWITCH_CLIENT_ID` を環境変数で上書きできます。

```powershell
$env:TWITCH_CLIENT_ID = "your_client_id"
$env:CLIPSCOPE_NOTIFY_SOUND_PATH = "C:\path\to\notify.wav"
python -m app.main --run-ui
```

データベースの保存先:

- 既定: `%APPDATA%\ClipScope\clipscope.db`
- 上書き: `CLIPSCOPE_DB_PATH` 環境変数

通知音ファイル:

- 推奨: `wav`
- 既定探索先:
  - `%APPDATA%\ClipScope\notify.wav`
  - 実行ファイルと同じフォルダの `notify.wav`
  - 開発環境の `assets/sound/notify.wav`

## 配布ビルド (Windows)

PyInstaller を使って onefile 形式でビルドします。

```powershell
.\tools\release\build_windows.ps1
```

出力先:

- `dist/ClipScope.exe`

配布用 ZIP を作成する場合:

```powershell
.\tools\release\package_windows.ps1 -Version 0.1.5
```

出力先:

- `release/ClipScope-v0.1.5-windows-x64.zip`

## Twitch Developer 設定 (配布時の案内用)

- OAuth Redirect URLs: `http://localhost` を登録
- Client Type は Twitch Developer Console の現在仕様に従って設定
- 認証方式: Device Code Flow

## ライセンス

MIT
