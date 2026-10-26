# 设计变量检查

[UI 规范](standards/ui.md)要求字体、圆角、颜色、间距只在设计变量模块中写字面量。配置或调整检查时读本文件。

[check_design_tokens.py](../scripts/check_design_tokens.py) 逐行扫描 Swift、OC 源码，模块外出现字面量即退出 1，输出 `路径:行: [规则] 原文`。基于正则，不解析语法；字符串中的同形文本可能误报，用基线或缩小规则处理，不在代码里绕开写法。

## 配置

项目新建 `.agents/design-tokens.json`：

```json
{
  "sources": ["App"],
  "modules": ["App/Shared/Theme"],
  "rules": ["font", "corner-radius", "color", "spacing"],
  "custom_rules": {"shadow": "shadowRadius\\s*[:=]\\s*\\d"},
  "baseline": ".agents/design-tokens-baseline.json"
}
```

- `sources`、`modules`：项目相对目录或文件；`modules` 内的文件豁免。未扫描到任何源文件时报错。
- `rules`：内置规则子集，省略为全部；`custom_rules` 追加项目规则（规则名 → 正则）。`extensions` 可覆盖默认的 `.swift`、`.m`、`.mm`、`.h`。
- 内置规则：`font`（`.system(size:)`、`Font.custom`、`systemFont(ofSize:)`、`UIFont(name:)` 等）、`corner-radius`、`color`（`Color(red:)`、`UIColor(white:)`、`colorWithRed:` 等）、`spacing`（`.padding(数字)`、`spacing: 数字`）。圆角与间距取值 0 放行；注释行不检查。

## 接入与存量

`install` / `setup` / `verify init` 会在缺失时生成 `.agents/design-tokens.json` 与日常 profile 中的 design-tokens 检查；已有文件不覆盖。也可手工在 `project-checks.json` 日常 profile 加一项，几秒完成，不需构建：

```json
"design-tokens": {
  "argv": ["python3", ".agents/skills/iOS/scripts/check_design_tokens.py"],
  "covers": ["App"],
  "inputs": ["App", ".agents/design-tokens.json", ".agents/design-tokens-baseline.json", ".agents/skills/iOS/scripts/check_design_tokens.py"]
}
```

已有项目首次启用时，单独建卡运行 `--update-baseline` 把存量违规写入基线并提交；之后基线只放行原有写法，同一文件新增相同写法也会失败。迁移存量后再次运行 `--update-baseline` 收缩基线；输出提示基线条目已不存在时同样清理。不得为通过检查把新增违规写入基线。
