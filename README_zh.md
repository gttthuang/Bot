# Job Bot

[English](./README.md) | [中文](./README_zh.md)

`jobbot` 會監控 Google Careers 搜尋結果頁，並在符合條件的職缺出現新增、更新或關閉時，發送 Discord 通知。

這個專案目前是為以下使用方式設計的：

- 公開 GitHub repo
- GitHub Actions 定時執行
- 之後新增監控條件時，優先只改 config
- 用獨立的 `state` branch 保存 `data/jobbot.db`

## 目前設定

目前使用的設定檔在 [configs/config.yaml](/Users/hshuang/Downloads/Bot/configs/config.yaml:1)。

現在監控的是：

- `Google`
- `Software Engineer`
- `FULL_TIME`
- `BACHELORS`
- `target_level=EARLY` 的 Taiwan / China
- `target_level=MID` 的 Taiwan / China

目前有兩組 subscription：

- `google_l3_tw_cn`
- `google_l4_tw_cn`

## 比對邏輯

Google Careers 不會公開內部職級，例如 `L3 / L4 / L5`。

這個 bot 現在只依賴兩件事：

- 你在 config 裡指定的 Google Careers 搜尋 URL
- Google 官方提供的 `Experience` badge：`early`、`mid`、`advanced`

## 系統流程

資料流如下：

`Google Careers URL -> 抓完整個搜尋結果頁（含分頁） -> parse jobs -> 和 SQLite 狀態比對 -> 產生事件 -> 套 subscription -> 發 Discord`

主要模組：

- `jobbot/sources/`：來源抓取與 parse
- `jobbot/service.py`：比對新舊資料並產生事件
- `jobbot/rules.py`：subscription 比對
- `jobbot/notifiers.py`：Discord webhook 訊息
- `jobbot/store.py`：SQLite 狀態保存

## 本機執行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL_L3='https://discord.com/api/webhooks/...'
export DISCORD_WEBHOOK_URL_L4='https://discord.com/api/webhooks/...'
JOBBOT_DRY_RUN=1 JOBBOT_LOG_LEVEL=DEBUG python -m jobbot
```

如果要真的送 Discord 通知，把 `JOBBOT_DRY_RUN=1` 拿掉即可。

可用環境變數：

- `JOBBOT_CONFIG`
  預設是 `configs/config.yaml`
- `JOBBOT_DRY_RUN`
  設成 `1` 時不會真的發通知
- `JOBBOT_LOG_LEVEL`
  例如 `DEBUG`、`INFO`

## 公開 GitHub Actions 設定

1. 把這個資料夾推到公開 GitHub repo。
2. 在 repo secrets 新增 `DISCORD_WEBHOOK_URL_L3` 和 `DISCORD_WEBHOOK_URL_L4`。
3. 開啟 GitHub Actions。
4. 手動跑一次 workflow，或等排程自動執行。

workflow 在 [.github/workflows/jobbot.yml](/Users/hshuang/Downloads/Bot/.github/workflows/jobbot.yml:1)。

它會做三件事：

- 從 `state` branch 還原 `data/jobbot.db`
- 執行 monitor
- 把更新後的 `data/jobbot.db` 寫回 `state` branch

這樣排程執行之間才會保留 dedupe 和 close detection 的狀態。

## State Branch

workflow 會把 SQLite 狀態檔寫到 `state` branch。

注意：

- 如果 repo 是公開的，`state` branch 也是公開的
- 這個 branch 只存監控狀態，不存 secrets
- Discord webhook 仍然放在 GitHub secrets，不會進 git

## 之後怎麼擴充

正常擴充方式是直接改 [configs/config.yaml](/Users/hshuang/Downloads/Bot/configs/config.yaml:1)。

常見改法：

- 新增一組 Google Careers 搜尋 URL
- 新增一組 subscription
- 把 Taiwan / China 拆成不同 subscription
- 之後再加 `advanced`

通常不需要改 code；只有這幾種情況才需要：

- Google 改了頁面格式
- 你要加非 Google 的來源
- 你要換通知管道，不再用 Discord

## 測試

```bash
.venv/bin/python -m unittest discover -s tests -v
```
