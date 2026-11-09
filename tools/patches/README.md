# tools/patches — 给 wewrite CLI 打的三个本地补丁

`uv tool install wewrite` 装的是独立 venv，provider 注册表和命令实现都写死在
`site-packages` 里，没有插件入口。这三处只能改源码，所以做成可重复执行的脚本：

| 脚本 | 改哪个文件 | 修什么 | 不修的后果 |
|---|---|---|---|
| `patch_image_providers.py` | `wewrite/toolkit/image_gen.py` | 新增 `sensenova`、`modelscope` 两个免费图源 | 只能用内置 provider（doubao / openai / gemini 等），要自己付费 |
| `patch_run_finish.py` | `wewrite/runs.py` | `run finish` 已封存后仍能从 `sources.yaml` 刷新来源计数 | 补录来源后再 finish，计数仍是旧值 |
| `patch_publish_digest_log.py` | `wewrite/toolkit/cli.py` | `publish` 打印的摘要改成实际发送值 | 传了 `--digest` 时日志显示的是解析前的值，容易误判发布结果 |

## 什么时候跑

- 想用那两个免费图源时（需要对应的 key，写进 `.wewrite/config.yaml` 的 `image.providers`）。
- **每次 `uv tool upgrade wewrite` 之后**——升级会覆盖 `site-packages`，补丁一起没了。

## 怎么跑

在**本目录下**执行（`_locate.py` 必须和脚本同目录）：

```bash
python patch_image_providers.py --check     # 看状态，不改文件
python patch_image_providers.py             # 应用，幂等，可重复跑
python patch_run_finish.py --restore        # 还原上一次的备份
```

`--restore` 只有 `patch_run_finish.py` 和 `patch_publish_digest_log.py` 提供；
`patch_image_providers.py` 想还原就把同目录的 `image_gen.py.orig` 覆盖回 `image_gen.py`。

全部补丁一次查完：

```bash
for f in patch_image_providers.py patch_run_finish.py patch_publish_digest_log.py; do
  python "$f" --check
done
```

## 实现说明

- 目标文件由 `_locate.py` 定位：先在 wewrite 自己的解释器下 `import` 取 `__file__`，
  取不到就去 `uv tool dir` 里递归找 `**/site-packages/<相对路径>`。
  不拼死 `Lib/site-packages`，因为 macOS/Linux 是 `lib/python3.x/site-packages`。
- 每个脚本应用前把原始文件备份成 `<文件名>.orig`，只备份一次，不会被后续重跑覆盖。
- 幂等：已打过的补丁再跑一遍内容不变；`patch_image_providers.py` 会把旧补丁块整体重放，
  所以补丁自身改版后直接重跑就能更新。
- 锚点找不到时会报错退出，不会静默跳过——CLI 大版本升级改了函数结构，就属于这种情况，
  需要人工看新代码再改脚本。

## 风险

这些补丁改的是别人包的源码，**升级即失效**。升级后先 `--check`，报「未应用」就重跑；
报锚点找不到说明上游改了结构，停下来人工核对，不要强行 `--force`。
