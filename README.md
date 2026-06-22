# 皎月连自动签到工具

自动登录 [皎月连](https://www.natpierce.cn) 检查签到状态，服务到期前自动提醒签到。

## 功能

- ✅ 自动登录
- ✅ 检查签到是否可用
- ✅ 可签到则尝试自动签到（如遇网易易盾验证码则推送通知提醒手动签到）
- ✅ 多渠道推送通知（Server酱 / Telegram Bot / Bark）
- ✅ GitHub Actions 定时运行（每天 8:00 / 16:00 / 22:00）

## 使用方式（GitHub Actions）

### 1. 将本仓库推送到 GitHub

### 2. 配置仓库 Secrets

前往 GitHub 仓库 → **Settings** → **Secrets and variables** → **Actions** → 添加以下 Secrets：

| Secret | 说明 | 必填 |
|--------|------|------|
| `NATPIERCE_USER` | 皎月连登录账号（手机号） | ✅ |
| `NATPIERCE_PASS` | 皎月连登录密码 | ✅ |
| `NATPIERCE_MAIL_USER` | 发件邮箱（推荐 QQ邮箱/163邮箱） | 选填 ⭐ |
| `NATPIERCE_MAIL_PASS` | 邮箱 **SMTP 授权码**（不是登录密码） | 选填 ⭐ |
| `NATPIERCE_MAIL_TO` | 收件邮箱（默认同发件邮箱） | 选填 |
| `NATPIERCE_SCT_KEY` | [Server酱](https://sct.ftqq.com) SendKey | 选填 |
| `NATPIERCE_TG_BOT_TOKEN` | Telegram Bot Token | 选填 |
| `NATPIERCE_TG_CHAT_ID` | Telegram Chat ID | 选填 |
| `NATPIERCE_BARK_KEY` | [Bark](https://day.app) Key (iOS) | 选填 |

> **至少配置一个推送渠道**（推荐邮箱，完全免费），否则签到结果无法通知到你。

### 邮箱配置说明（推荐）

以 **QQ邮箱** 为例：
1. 登录 QQ邮箱 → **设置** → **账户**
2. 找到 **POP3/SMTP服务** → 点击 **开启**
3. 按提示发送短信后获取 **授权码**（16位字母）
4. 在 GitHub Secrets 中设置：
   - `NATPIERCE_MAIL_USER` = `你的QQ号@qq.com`
   - `NATPIERCE_MAIL_PASS` = 上面获取的 **授权码**

> **注意**：`MAIL_PASS` 是授权码，不是你QQ邮箱的登录密码！

**163邮箱** 类似：登录 → 设置 → POP3/SMTP → 开启 → 获取授权码。

其他邮箱（126/Gmail/Outlook）脚本会自动识别 SMTP 服务器，也可手动设置 `MAIL_SMTP_HOST` 和 `MAIL_SMTP_PORT`。

### 3. 触发方式

- **自动**：每天 UTC 0:00 / 8:00 / 14:00（北京时间 8:00 / 16:00 / 22:00）运行
- **手动**：仓库 → **Actions** → **皎月连自动签到** → **Run workflow**

## 本地运行

```bash
cd natpierce-sign
pip install -r requirements.txt

export NATPIERCE_USER="你的手机号"
export NATPIERCE_PASS="你的密码"
# 可选推送
export SCT_KEY="你的 Server酱 Key"
# 或
export TG_BOT_TOKEN="你的 Bot Token"
export TG_CHAT_ID="你的 Chat ID"
# 或
export BARK_KEY="你的 Bark Key"

python sign.py
```

## 签到说明

皎月连的签到是**服务续期机制**，不是每日签到。当服务即将到期时才可以签到。如果签到需要 **网易易盾验证码**，脚本会推送通知提醒你**手动打开签到页面**完成验证码。

签到页面：https://www.natpierce.cn/pc/sign/index.html

## 项目结构

```
natpierce-sign/
├── sign.py              # 主签到脚本
├── requirements.txt     # Python 依赖
└── .env.example         # 环境变量模板

.github/workflows/
└── natpierce-sign.yml   # GitHub Actions 定时工作流
```
