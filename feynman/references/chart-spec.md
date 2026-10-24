# 图表脚本规范

当宿主可以执行本地 Python 和浏览器时，使用 `../scripts/render_chart.py` 生成一致的 SVG、HTML 和 PNG。脚本只使用 Python 标准库；PNG 需要本机安装 Edge 或 Chrome。

## 调用

从 Skill 根目录运行：

```powershell
& <Python解释器> scripts/render_chart.py chart.json `
  --out-dir chart-output --theme dark --width 720
```

输出：

```text
chart-output/chart.svg
chart-output/chart.html
chart-output/chart.png
```

显示 PNG 前必须实际检查：文字是否被截断、图例是否对应、坐标和单位是否清楚、是否存在误导性基线。

## 允许的图形

- `line`：有序变化、收敛、响应曲线；
- `bar_h`、`bar_v`：类别数量对比，条形图必须从零开始；
- `bar_h_grouped`：少量分类下比较两组方法；
- `scatter`：两个数值变量的关系。

数据变化可使用最多三条线的 `line`。函数、导数、积分、向量和几何构造改用 [math-figures.md](math-figures.md) 与 `render_math_figure.py`，不要把所有数学问题都压成折线图。

数学函数、序列、极限、向量和坐标关系必须设置 `"math_axes": true`，并通过 `x_values` 提供真实数值横坐标。渲染器会绘制穿过原点的横轴、纵轴、箭头和原点 `O`。

## 折线图示例

```json
{
  "kind": "line",
  "math_axes": true,
  "x_labels": ["1", "2", "3", "4", "5"],
  "x_values": [1, 2, 3, 4, 5],
  "x_label": "n",
  "y_label": "xₙ",
  "series": [
    {"label": "A", "values": [1.0, 0.5, 0.3333, 0.25, 0.2]},
    {"label": "B", "values": [-1.0, 0.5, -0.3333, 0.25, -0.2]},
    {"label": "C", "values": [-1.0, 1.0, -1.0, 1.0, -1.0]}
  ]
}
```

不要在图下直接总结哪条线正确。图后只提出一个解释性问题，让用户完成判断。

## 失败回退

- 没有 Python：使用 Mermaid、Markdown 表格或文字示意；
- 没有 Edge/Chrome：保留 SVG 和 HTML，不声称已经生成 PNG；
- 数据不足：画明确标注的示意图，不伪造数值；
- 绘图后发现问题：修正 JSON 并重新生成，不展示未经检查的图片。
