# 接入指南

讀者：App 開發者
型別：接入指南

本指南帶你從零接入登入元件。共用的登入流程概念見 [登入流程總覽](overview.md)。

## 前置條件

- 已建立專案並取得 client id。
- 閱讀 [OAuth 2.0 規格](https://www.rfc-editor.org/rfc/rfc6749) 的授權碼流程。
- 使用 v1.2.0 以上的 SDK。

## 安裝

1. 執行 `npm install sample-login-kit`。
2. 確認 `package.json` 列出該套件。

## 設定

1. 建立 `config.json`。
2. 填入 client id：

   ```json
   {"clientId": "abc"}
   ```

3. 匯入設定並初始化。

### 離線模式

> 僅在主幹，尚未發版。

啟用後，登入頁在斷線時顯示本機快取的提示。

| 選項 | 說明 |
|------|------|
| `offline` | 離線模式（僅在主幹，尚未發版） |
| `retry` | 失敗後重試的次數 |

```kotlin
val mode = Mode.Offline // 僅在主幹，尚未發版
```

## 驗證

1. 啟動範例 App。
2. 點擊登入並完成授權。
3. 確認畫面顯示使用者名稱。

校驗碼範例：`sha256: 3f2a9c1e8b4d`。

| 平台 | 行為 | 驗證 |
|------|------|------|
| Android 15 | 登入成功 | 已實測（2026-10-01，Pixel 6 API 35） |
| iOS 18 | 登入成功 | 未實測 |

## 參考

- [登入流程總覽的登入流程](overview.md#登入流程)
- [README 的文件導覽](../README.md#文件導覽)
