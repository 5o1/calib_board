# 采集台统一标定板 station_calib_board

独立的 A3 定尺打印标定板：OpenCV ChArUco 几何标定、8 级名义中性灰阶、Calibrite ColorChecker Classic Mini 粘贴位。无需 gamepad_vla，也不控制机器人。许可证选择 MIT，见 `LICENSE`。

规格来源和设计权衡见 [调研](docs/research.md)，本地验证和两次审阅者裁决见 [交付报告](docs/report.md)。实物打印、安装和真实相机验证尚未执行。

## 固定规格 v1.0.0

规格唯一来源：`spec/board_v1.json`。所有版面坐标使用 **mm**，位姿工具平移使用 **m**。修改图案或排版后必须更新版本并重新生成、验证；检测必须使用对应规格。

| 项目 | 规格 |
|---|---|
| 板 ID / 版本 | STATION-CALIB-001 / 1.0.0 |
| 页面 | A3 横向 420×297 mm，MediaBox 按 72/25.4 pt/mm 固定 |
| ChArUco | 7×6 **格**，6×5 内角点，字典 DICT_4X4_50，marker ID 0–20 |
| 格边 / 标记边 | 44 / 39.5 mm，单层黑边；每个 marker 含边框共 6×6 cell |
| 图案尺寸 | 308×264 mm；图案左上角位于纸张左上角向右 25、向下 20 mm |
| 板坐标 | 图案左上外角为原点；面对印刷面 X 向右、Y 向下、Z 指入板内，右手系；OpenCV 非 legacy 模式 |
| 灰阶 | G1–G8，22×22 mm；名义 sRGB 为 (v,v,v)，v=16,48,80,112,144,176,208,240；名义值，不是实测反射率 |
| 色卡位 | 板坐标 (314,125) 起，63.5×109 mm，竖放；官方外形为 109×63.5 mm，不印彩色块 |
| X 校验尺 | (45,270) 到 (145,270)，100 mm |
| Y 校验尺 | (−12,40) 到 (−12,140)，100 mm |
| 安装孔 | 直径 3.2 mm 圆 + 总长 10 mm 十字线 + H1–H4 编号；只印定位标记，是否打孔由实际安装决定 |

灰阶左上角依次为 (317,15)、(342,15)、(317,41)、(342,41)、(317,67)、(342,67)、(317,93)、(342,93)。色卡局部坐标绕板 Z 轴转 +90°，精确齐次变换在 JSON 的 `colorchecker_slot.T_board_card_mm`。纸张、棋盘每个方格、每个 marker、每个内角点、灰阶、色卡框、孔、文字基线、尺和每条刻度的坐标均在 JSON 中。

| 孔号 | 板坐标中心 (X,Y) mm | 纸坐标（左上为原点）mm |
|---|---|---|
| H1 左上 | (−15,−10) | (10,10) |
| H2 右上 | (385,−10) | (410,10) |
| H3 右下 | (385,267) | (410,287) |
| H4 左下 | (−15,267) | (10,287) |

H1→H2 沿 +X，H2→H3 沿 +Y，顺时针编号。孔中心矩形 **400×277 mm**，两条对角线均 **486.54804 mm**（精确值以 JSON 为准）。孔心距纸边均 10 mm；自动检查圆、十字线及编号包围盒与棋盘、灰阶、色卡框、刻度尺的净距 ≥5 mm。

## 工作距离与使用边界

主档：1280×720，fx=906.561、fy=905.986、cx=647.896、cy=362.233；备用档：640×480，fx=604.374、fy=603.991、cx=325.264、cy=241.489；均 D=0。`examples/camera_*.json` 给出完整输入。

以图案中心对准光轴、板法线与视线夹角 45°、对倾斜方位每 5° 扫描、逐 cell 投影计算（取两个局部投影基向量的最小奇异值，包含斜向压缩）：

- 主档 0.9 m：最小 **3.526 px/cell**，达到 3.5 px 要求；45° 下对应最大距离约 **0.909 m**。
- 备用档 0.8 m：最小 **2.559 px/cell**，未达到 3 px；要达到 3 px，45° 下距离需约 **≤0.632 m**。距离更近仍须确保板和所需灰阶在画面内。
- 1.0 m 或更斜时 cell 预算降低。主档 0.9 m、**法线夹角 60°** 仅约 2.351 px/cell，不能宣称满足上述预算。俯视角指视线与台面夹角，与法线夹角互余；例如俯视 45–60° 对应法线夹角 45–30°。

这些是几何采样预算，不是实拍识别概率。标记较大，白边仅 2.25 mm，低于 OpenCV 的 0.7 cell 建议；这是 A3、工作距离与孔位/功能区共同限制下的权衡。合成闭环通过，真实打印后仍需按下文实拍验收。

## 本地环境与运行

已在本仓库 `.venv` 安装并验证；完整版本锁定在 `requirements.lock.txt`，直接依赖也在 `requirements.txt`。本次 Python 为 3.14.7；建议复现使用相同 Python 与 lock，其他 Python/平台未验证。不要在别的项目环境安装或混装另一份 OpenCV wheel。

```bash
cd /path/to/station_calib_board
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip check
.venv/bin/python -m calib_board.generate --spec spec/board_v1.json --output out/board_v1_A3.pdf
.venv/bin/python -m pytest -q --junitxml=docs/pytest-results.xml
```

生成器输出确定性矢量 PDF 和同名 **300 DPI** PNG 预览。棋盘、marker 的每一 cell 和灰阶均为矢量矩形；PNG 仅供查看，**打印 PDF**。PDF 纳入 Git 管理，`.venv` 和预览/合成图由 `.gitignore` 排除。

## 打印、贴板与验收

使用 A3 横向，**按实际尺寸 / 100% 打印，不要“适合页面”**。关闭应用和打印机驱动的缩放、自动适配及省墨模式，建议哑光纸。确认四角孔及页面边缘的尺均未被打印机裁切。

打印后先测量，再贴板：

1. 量 X、Y 两根 100 mm 刻度尺的端点中心，允许 99.5–100.5 mm。
2. 在棋盘中央与边缘分别量格边，44 mm 允许 43.78–44.22 mm；建议跨多个格量总长度后除以格数。
3. 量 H1–H2=400 mm、H1–H4=277 mm，并量 **H1–H3 和 H2–H4 对角孔中心距**，与 JSON 的 `hole_rectangle.diagonal_mm` 比较。各项相对偏差须 ≤0.5%。
4. 任一项偏差 >0.5% 判不合格，重新检查打印设置/打印机，勿直接拿名义尺寸求位姿。
5. 复制 `spec/print_measurements.template.json` 为 `docs/measurements/<日期>_<板ID>.json`，记录打印机、纸张、尺具、各实测值、日期和验收人；模板空值表示未测，不能当作合格。把贴板后的复测、板厚与摆放测量一起记录。

用平整硬质底板，如 KT 板或亚克力；均匀粘贴，避免气泡、褶皱和翘曲，贴后复测。孔位只表示固定点，不要让螺钉、胶带或夹具侵入功能区。安装板厚和粘接层厚度一起计入“印刷面高出台面”的测量。

## 摆放和测量

推荐板平放、正面朝上，量 **H1、H2 两个孔中心**分别到台面后沿和左侧边的垂直距离。不要量纸角或孔外缘。长基线降低角度测量误差；换用任意另外两孔也支持，但须准确编号。

独立使用时定义台面局部世界系：原点在台面后沿与左侧边交点；X 从后沿指向前沿，Y 从左边指向右边，Z 向上，台面 Z=0。若与采集台既有 world 对接，其方向约定来自 gamepad_vla 的 `references/station_measurements.md`（2026-10-16 只读核对）：X 从立柱指向桌前沿，Y 从左侧指向右侧，Z 向上、地面 Z=0。记录中台面高度 767 mm。**本仓库不加载该项目**；用 `world_back_left_m` 显式填台面后左角在实际 world 中的 [X,Y,Z]。不要把台面 Z=0 与地面 Z=0 混用；台面高度也不是相机高度。X/Y 原点偏移须结合实际 world 定义测量，不能由高度推定。

测量输入（下面数值仅演示，非采集台实测）：

```json
{
  "hole_measurements": [
    {"id":"H1", "from_back_edge_mm":100, "from_left_edge_mm":200},
    {"id":"H2", "from_back_edge_mm":500, "from_left_edge_mm":200}
  ],
  "board_surface_above_table_mm":5,
  "world_back_left_m":[0,0,0],
  "distance_tolerance_mm":2
}
```

算法把各孔世界坐标写成 `(距后沿, 距左边, 印刷面高度)`，加上后左角偏移。设两孔板平面坐标差为 db，世界平面差为 dw，则 θ=atan2(dw.y,dw.x)+atan2(db.y,db.x)，板旋转列向量为 X=(cosθ,sinθ,0)、Y=(sinθ,−cosθ,0)、Z=(0,0,−1)。平移取两孔 `p_world − R p_board` 的平均。两孔间距与规格不一致超过默认 2 mm 时拒绝输入；该一致性检查不代表测量精度。只量两孔不能观测板翘曲或倾斜，算法明确假设板平放。板倾斜/竖放时，输入完整变换文件 `{"T_world_board": [[...],[...],[...],[0,0,0,1]]}`，平移单位 m。

每张图检测得到 `T_camera_optical_board`，求逆并组合：`T_world_camera_optical = T_world_board @ inv(T_camera_optical_board)`。输出 `pose_xyz_qw_qx_qy_qz` 即 **[x,y,z,qw,qx,qy,qz]**，四元数单位化，qw≥0；ROS optical 为 X 右、Y 下、Z 前，不额外引入 camera_link 旋转。

多张图必须来自**同一固定相机、同一固定板摆放**。用平移均值和 SO(3) 投影均值融合，输出留一图 jackknife 标准差；仅一张时不确定性为 null。该估计只表示帧间重复性，不包含内参、尺量、平面度、打印尺寸等系统误差。移动板后应重新测量并单独处理。

## 工具示例

检测支持 JSON 的 K（3×3 或 9 个值）、D，以及 ROS `camera_info` YAML/JSON 的 `camera_matrix.data` / `distortion_coefficients.data`。使用与图像对应的分辨率和 OpenCV pinhole 畸变，支持 plumb_bob / rational_polynomial；不支持 fisheye。未自动缩放内参。

```bash
.venv/bin/python -m calib_board.detect /path/to/frame.png \
  --intrinsics /path/to/camera_info.yaml --spec spec/board_v1.json \
  --output out/detection.json --overlay out/detection_overlay.png

.venv/bin/python -m calib_board.extrinsics out/detection.json \
  --placement examples/placement_holes.json --output out/extrinsics.json

# 多帧固定板、固定相机
.venv/bin/python -m calib_board.extrinsics out/detection1.json out/detection2.json out/detection3.json \
  --placement /path/to/measured_placement.json --output out/extrinsics.json

.venv/bin/python -m calib_board.gray_ramp /path/to/frame.png \
  --detection out/detection.json --output out/gray.json
```

检测输出角点 ID/像素坐标、物点、内参、板相对相机位姿和重投影误差中位数/P95（px），并保存坐标轴与角点叠加图。使用至少 6 个非共线角点，先用官方 CharucoDetector、matchImagePoints、solvePnP，再做 LM。额外尝试半径 2 px 的 cornerSubPix；仅当整体 RMS 改善至少 10% 才采纳，并记录两个候选 RMS。验收仍是 2 mm / 0.2° / 0.5 px，未改变。

灰阶工具按位姿投影每块中央 60% 区域中的 20×20 网格，双线性采样平均 RGB（输出为 RGB 顺序，8 bit），越界块标为不可用；假设被采样块未被遮挡。用无明显截断的中间名义灰阶估计 `[G/R,1,G/B]` 白平衡增益，检查亮度顺序、≥250 高光截断、≤5 暗部压黑，并报告码值直线拟合残差。打印、照明和相机响应都影响结果，名义灰阶不是实测反射率，这些结果不能证明辐射线性，**不是完整颜色校正**。

拍摄时使用均匀漫射光，避免反光与阴影，保持清晰对焦，锁定分辨率、焦距和内参。做内参标定时应覆盖画面不同区域和适度倾角；本工具只用已知内参求外参，不估计内参。移动相机或改变镜头后重新标定。

## 采集台最小副本

采集台 `~/calibration_board/` 只保存 PDF、规格、此 README，以及 `calib_board/__init__.py`、`common.py`、`detect.py`。副本不含生成器、pytest、合成图、外参和灰阶工具；完整工具在本仓库。复制过程只用 shell/tar 在该目录写入，不在采集台运行标定程序或安装依赖。

在已具备 OpenCV/numpy/PyYAML 的获授权环境中，从副本目录执行 `python -m calib_board.detect ...`；环境准备属于后续独立操作，本次未在采集台执行。README 中的 `.venv`、examples、其他工具及文档路径适用于完整仓库。
