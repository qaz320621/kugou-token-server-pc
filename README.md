# PC 版 Token 登录服务（Python）

酷狗扫码登录 + Token 管理（中间人），供 MusicFree 插件拉取配置。

## 依赖关系

```
父项目：kugou-musicfree-suite（本服务是其子项目）
├── 运行依赖：Python 3 + pip 包 qrcode[pil]（其余用标准库）
└── 被谁依赖：kugou-musicfree-plugin（插件运行时 GET /token 拉取配置）
    —— 与 kugou-token-server-android 功能等价，二选一
```

## 运行

```bash
pip install qrcode[pil]
python token_server.py        # 默认端口 8765
```

Windows 也可双击 `启动Token服务.bat`。

## 使用

1. 浏览器打开 `http://127.0.0.1:8765/`
2. 点「📱 扫码登录」→ 手机酷狗 App 扫二维码 → 手机/确认页点【确认登录】
3. token 自动写入 `config.json`，插件（MusicFree）从 `GET /token` 拉取

## 接口

| 路径 | 说明 |
|---|---|
| `GET /login/qr` | 生成酷狗官方登录二维码（PNG），并启动后台轮询 |
| `GET /login/status` | 登录状态（waiting/scanned/success/fail） |
| `GET /token` | 返回配置 JSON（插件用） |
| `POST /save` | 手动保存配置（备用） |
| `GET /` | 管理网页 |

## 安全

- `config.json` 存本地，不入库（参考 `config.example.json` 结构）
- 初始为空，扫码登录成功后写入
