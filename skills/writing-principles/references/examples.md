# 改寫前後對照

三組片段取自一個登入頁前端 repo 的文件改寫（README 與架構說明），已去識別化：組織、產品、repo、品牌與 wiki 連結都換成通用名稱，路徑保留一般化形式。片段只取能說明原則的部分；原則編號對應 `SKILL.md`。

## 1. README 首段

**對應原則**：1（加檔頭並分型）、3（拿掉「目前」）、6（首句給結論，長段拆短）、9（交叉引用寫章節名稱、連結收斂）。

**改寫前**：入口檔沒有檔頭；首段一口氣放部署、頁面清單、狀態與六個連結。

```markdown
# web-login

登入頁的前端。本 repo 是純靜態頁（prerender，無 runtime server），部署在物件儲存、由 CDN 對外，和 `<org>/api-login` 共用同一個 origin，掛在 `/login/*`（見 [`docs/adr/0002-static-page-api-owns-sso.md`](docs/adr/0002-static-page-api-owns-sso.md)）。prerender 的頁面清單見 `react-router.config.ts` 的 `prerender`：`/login/`、`/login/404/`、兩個法律文件頁與六個品牌登入頁（清單見 `app/brands.ts`）。登入卡片依 hydrate 狀態與 `request_id` 是否可用分三態（見 `app/components/login-card.tsx` 開頭註解）；Google、Facebook、LINE 社群登入已接 api 的 start 端點，Apple 按鈕維持 disabled（api 沒有 Apple 的 start 端點）。SSO 略過登入頁目前只是 api 的設計意圖、api 尚未實作。產品與設計脈絡見 [`PRODUCT.md`](PRODUCT.md)／[`DESIGN.md`](DESIGN.md)；架構決策見 [`docs/adr/0001-rebuild.md`](docs/adr/0001-rebuild.md)、[`docs/adr/0002-static-page-api-owns-sso.md`](docs/adr/0002-static-page-api-owns-sso.md)。
```

**改寫後**：檔頭兩行；首段只講這個 repo 是什麼與去哪找；登入流程的角色另立 H2，一段講一件事。

```markdown
# web-login

讀者：開發者、SRE
型別：入口

登入頁的前端：prerender 的純靜態頁（無 runtime server），部署在物件儲存、由 CDN 對外，和 `<org>/api-login` 共用同一個 origin，掛在 `/login/*`。產品與設計脈絡見 [`PRODUCT.md`](PRODUCT.md)；工作規則見 [`docs/working-rules.md`](docs/working-rules.md)；架構決策見 [`docs/adr/0002-static-page-api-owns-sso.md`](docs/adr/0002-static-page-api-owns-sso.md)。

## 本 repo 在登入流程中的角色

登入頁是 api 自己的登入畫面，不是依賴方（client）。client 先把使用者導向 api 的 authorize 端點，api 驗證後 302 到登入頁並帶 `request_id`。

登入頁只負責呈現登入方式與錯誤提示；provider callback、SSO 與 token 都在 api（見 [`docs/adr/0002-static-page-api-owns-sso.md`](docs/adr/0002-static-page-api-owns-sso.md)〈決策〉）。
```

## 2. 架構文件的「名詞」節

**對應原則**：4（拿掉釘死 commit 的連結與出處基準行）、11（共用名詞只留一個權威版，本文一句話加連結）、1（說明文件的檔頭）。

**改寫前**：每個名詞各帶一條釘死 commit 的連結，文件開頭還有出處基準行。

```markdown
出處基準：本 repo `<7 位 hex>`、api-login `<7 位 hex>`；文中出處皆指這兩個 commit。

## 名詞

- **client（依賴方，RP）**：想讓使用者登入的網站或 App，每個 client 在 api 註冊 `client_id`、`redirect_uris` 與 `brand`（api [D6](https://github.com/<org>/api-login/blob/<40 位 hex>/docs/DECISIONS.md)）。
- **api**：身分後端 `<org>/api-login`，對 client 扮演 OpenID Provider（api [D1](https://github.com/<org>/api-login/blob/<40 位 hex>/docs/DECISIONS.md)）。
- **provider**：社群登入的來源。api 目前註冊的是 Facebook、Google、LINE（api `cmd/api/setup.go` 的 `federationProviders`），沒有 Apple。
```

**改寫後**：檔頭宣告讀者與型別；名詞的權威定義在 wiki 共用頁，這裡只留一句話加連結。

```markdown
讀者：維護者、SRE
型別：說明

## 名詞

client（依賴方，RP）、api（身分後端，對 client 扮演 OpenID Provider）與 provider（社群登入的來源：Facebook、Google、LINE，沒有 Apple）的定義與角色見 [共用說明〈總覽〉](<wiki 連結>)。「登入頁」在本文指本 repo。
```

## 3. 「頁面與 route」表拆成兩表

**對應原則**：12（多屬性的同構項目用表格，不塞進單一儲存格）、6（表格格保持短）、3（拿掉「目前是」）。

**改寫前**：一列用括號把六個品牌的網址一次列完；另一列的儲存格同時講內容、現況與檔案。

```markdown
| 網址 | route 檔 | 內容 |
|------|----------|------|
| `/login/<brand>/`（`brand-a`、`brand-b`、`brand-c`、`brand-d`、`brand-e`、`brand-f`） | 同一個 `app/routes/home.tsx`，每個品牌各註冊一次 | 品牌登入頁：同一張登入卡片，換成該品牌的 logo 與品牌色 |
| `/login/terms/` | `app/routes/terms.tsx` | 會員服務條款；條款頁目前是標示為「假內容」的暫代頁（`app/legal-links.ts`、`app/legal/terms.ts`） |
```

**改寫後**：品牌各列一行放進第二張表，第一張表的儲存格只留一件事。

```markdown
| 網址 | route 檔 | 內容 |
|------|----------|------|
| `/login/<brand>/`（六個品牌，網址見下表） | 同一個 `app/routes/home.tsx`，每個品牌各註冊一次 | 品牌登入頁：同一張登入卡片，換成該品牌的 logo 與品牌色 |
| `/login/terms/` | `app/routes/terms.tsx` | 會員服務條款；是標示為「假內容」的暫代頁，文字在 `app/legal/terms.ts` |

六個品牌頁的網址與品牌（節錄前三列）：

| 網址 | 品牌 |
|------|------|
| `/login/brand-a/` | brand-a |
| `/login/brand-b/` | brand-b |
| `/login/brand-c/` | brand-c |
```
