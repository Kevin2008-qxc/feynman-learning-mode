# 数学构图规范

数学提示图使用 `../scripts/render_math_figure.py`。该脚本生成静态 SVG、HTML 和 PNG，并默认绘制带箭头的直角坐标系、原点 `O`、刻度与淡网格。

它借鉴 GeoGebra 的“数学对象直接可见”原则，但不复制 GeoGebra 的界面、素材或运行时，也不依赖其网络服务。

## 构图原则

- 一张图只解释一个关系；
- 曲线、切线、割线、渐近线和区域使用不同线型；
- 颜色保持一致，但不能只靠颜色区分；
- 关键对象直接标注，不强制另加图例；
- 所有数学结论必须来自公式、可靠数据或明确示意；
- 不执行表达式源码，模型先生成可信的采样点或几何坐标。

## JSON 对象

顶层字段：

- `title`、`subtitle`、`x_label`、`y_label`；
- `view`：`{"x": [xmin, xmax], "y": [ymin, ymax]}`；
- `aspect`：函数图可用 `"auto"`；圆、角、距离和几何构造必须使用 `"equal"`；
- `grid`：是否显示网格，默认 `true`；
- `curves`：函数曲线，使用 `points` 点列；
- `segments`：割线、切线、半径、弦等；
- `vectors`：带箭头向量；
- `circles`：圆心与半径；
- `points`：关键点及坐标标签；
- `guides`：水平或垂直虚线、渐近线、阈值；
- `bands`：水平或垂直区间阴影。

## 导数示例

```json
{
  "title": "割线趋近切线",
  "x_label": "x",
  "y_label": "y",
  "aspect": "auto",
  "view": {"x": [-1.5, 2.5], "y": [-1, 5]},
  "curves": [
    {
      "label": "f(x)=x²",
      "color": "#1D9E75",
      "points": [[-1, 1], [-0.5, 0.25], [0, 0], [0.5, 0.25],
                 [1, 1], [1.5, 2.25], [2, 4]]
    }
  ],
  "segments": [
    {"from": [0, 0], "to": [2, 4], "style": "dashed", "label": "割线"}
  ],
  "points": [
    {"at": [0, 0], "label": "P", "label_offset": [-18, 16]},
    {"at": [2, 4], "label": "Q", "label_offset": [8, -8]}
  ]
}
```

## 极限示例

- 用水平 `guides` 画 `y=ε` 与 `y=-ε`；
- 用水平 `bands` 标出 `(-ε, ε)`；
- 用垂直 `guides` 标出阈值 `N`；
- 用 `curves` 比较收敛、摆动收敛与不收敛；
- 图后只问用户如何判断，不在图上公布答案。

## 调用

```powershell
& <Python解释器> scripts/render_math_figure.py figure.json `
  --out-dir figure-output --theme dark --width 760
```

输出 `math.svg`、`math.html` 和 `math.png`。

## 质量门槛

- 曲线必须裁剪在绘图区内；
- 横纵轴、箭头、原点 `O`、刻度和标签必须可见；
- 刻度标签不能互相重叠；
- 关键点、切线、渐近线和阴影区域不能遮挡主体；
- 图例与直接标签必须和实际对象一致；
- PNG 必须实际打开检查，不能只检查是否生成；
- 画面过密时拆成两张，或只保留解释当前误区所需的对象。
