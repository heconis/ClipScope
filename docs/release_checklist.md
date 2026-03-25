# ClipScope リリースチェックリスト

## 1. 事前確認

- [ ] `python -m app.main --run-ui` で起動できる
- [ ] Twitch 認証が完了する
- [ ] 監視開始 / 停止が動作する
- [ ] クリップ一覧の更新・選択・削除が動作する
- [ ] OBS の Browser Source で再生と切り替えが動作する

## 2. ビルド

- [ ] `.venv` を有効化
- [ ] `.\tools\release\build_windows.ps1` を実行
- [ ] `dist/ClipScope.exe` が生成される
- [ ] `.\tools\release\package_windows.ps1 -Version 0.1.7` を実行
- [ ] `release/ClipScope-v0.1.7-windows-x64.zip` が生成される

## 3. 配布物確認

- [ ] 初回起動でクラッシュしない
- [ ] セットアップタブから認証導線が完結する
- [ ] 設定保存 / 初期化が動作する
- [ ] 終了時に致命的エラーが出ない

## 4. ユーザー向け同梱

- [ ] `README.md`
- [ ] `LICENSE`
- [ ] `RELEASE_NOTES.md`
- [ ] Twitch Developer 設定手順（必要なら別紙）
