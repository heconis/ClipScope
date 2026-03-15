# ClipScope v0.1.0 リリースノート

リリース日: 2026-03-15

## 概要

初回リリースです。  
Twitch クリップの監視、一覧管理、OBS Browser Source への再生連携を 1 つの Windows アプリとして提供します。

## 主な機能

- Twitch Device Code Flow 認証
- ログインユーザーのチャンネルをポーリング監視
- クリップ一覧の表示 / 手動更新 / 削除
- クリップ選択で OBS 再生ページへ反映
- 同一クリップ再選択時の再生リトライ対応
- 再生済み / 未再生ステータス表示
- 設定（保持件数、取得日数、ポーリング間隔、ローカルポート）の保存 / 初期化

## 配布物

- `ClipScope\ClipScope.exe`
- `README.md`
- `LICENSE`
- `RELEASE_NOTES.md`

## 注意事項

- 本アプリには既定の Twitch Client ID を同梱しています。
- 必要に応じて `TWITCH_CLIENT_ID` 環境変数で上書きできます。
- OBS にはブラウザソースとしてアプリのローカル再生 URL を設定してください。
- Windows Defender などの環境では初回起動時に確認ダイアログが出る場合があります。
